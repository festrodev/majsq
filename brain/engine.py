"""One turn, for every surface.

Telegram and the web both end up here. A surface decides how to *render* a
turn — inline keyboards, generative UI — and never what a turn *means*. That
keeps the two experiences honest: the same question, the same picks, the same
consent rules, whichever door you came through.

The engine is deliberately usable with no model key at all. ``respond`` reads
the conversation, decides what is missing, searches and ranks entirely
deterministically; the model is asked only to phrase the reply, and if it is
absent or errors the deterministic phrasing ships instead. A demo that depends
on an API key being live at 15:00 on a Saturday is not a demo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from brain import categories, ranking, reading, search, slots
from core.models import Conversation, Membership, PickSet, Turn

logger = logging.getLogger(__name__)

# How many past messages the agent reads for constraints. Long enough to catch
# "on est 6" three messages ago, short enough that last Tuesday's plan does not
# contaminate tonight's.
CONTEXT_MESSAGES = 12

# Offer the connect nudge after this many turns without a connected member,
# and at most once a day per conversation.
NUDGE_AFTER_TURNS = 3


@dataclass
class Reply:
    """What a surface renders.

    Exactly one of ``question`` or ``picks`` is meaningful at a time: the agent
    either needs something, or it has an answer.
    """

    text: str = ""
    question: dict | None = None
    picks: list[dict] = field(default_factory=list)
    share_id: str = ""
    map_url: str = ""
    state: dict = field(default_factory=dict)
    suggest_connect: bool = False
    poll: dict | None = None

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "question": self.question,
            "picks": self.picks,
            "share_id": self.share_id,
            "map_url": self.map_url,
            "state": self.state,
            "suggest_connect": self.suggest_connect,
            "poll": self.poll,
        }


def _recent_messages(conversation: Conversation) -> list[str]:
    turns = (
        Turn.objects.filter(conversation=conversation, role=Turn.Role.USER)
        .order_by("-created_at")[:CONTEXT_MESSAGES]
        .values_list("text", flat=True)
    )
    return list(reversed([text for text in turns if text]))


def _consenting_tastes(conversation: Conversation, constraints) -> list[ranking.Taste]:
    """Taste profiles for this conversation, consent checked on every turn.

    The consent flag is read here, live, *before* any profile is fetched or
    read from cache — so a member who switches it off is excluded on the very
    next turn even while their profile is still warm.
    """
    from festro import client

    tastes: list[ranking.Taste] = []
    memberships = (
        Membership.objects.filter(conversation=conversation)
        .select_related("participant", "participant__festro_link")
    )
    for membership in memberships:
        if conversation.is_group and not membership.use_my_taste:
            continue
        link = getattr(membership.participant, "festro_link", None)
        if link and link.is_live:
            profile = client.fetch_profile(link.credential)
            if profile:
                tastes.append(
                    ranking.Taste.from_profile(
                        profile, label=membership.participant.display_name
                    )
                )
                continue
        # No Festro history: what they said in the chat still counts, so a
        # guest shapes the picks instead of dragging the group minimum down.
        if constraints.stated_tags:
            tastes.append(
                ranking.Taste.from_stated(
                    tags=constraints.stated_tags,
                    label=membership.participant.display_name,
                )
            )
    return tastes


def _should_nudge(conversation: Conversation, tastes: list[ranking.Taste]) -> bool:
    if any(not taste.synthetic for taste in tastes):
        return False  # somebody is already connected
    if Turn.objects.filter(conversation=conversation, role=Turn.Role.USER).count() < NUDGE_AFTER_TURNS:
        return False
    last = conversation.connect_nudged_at
    if last and (timezone.now() - last).total_seconds() < 24 * 3600:
        return False
    return True


def _public_pick(event: dict) -> dict:
    """The shape that reaches a chat message and the map page.

    Public fields only. This is what an unguessable share link exposes, so
    anything private must not be in it — including the ``score`` the ranker
    attached and any reason that could name a person.
    """
    return {
        "short_id": event.get("short_id"),
        "title": event.get("title"),
        "venue_name": event.get("venue_name"),
        "city": event.get("city"),
        "latitude": event.get("latitude"),
        "longitude": event.get("longitude"),
        "start_datetime": event.get("start_datetime"),
        "start_time_known": event.get("start_time_known", True),
        "end_datetime": event.get("end_datetime"),
        "is_free": event.get("is_free"),
        "tags": event.get("tags") or [],
        "organizer_name": event.get("organizer_name"),
        "url": event.get("url"),
        "why": event.get("why", ""),
    }


def respond(
    *,
    conversation: Conversation,
    text: str = "",
    chosen: dict | None = None,
) -> Reply:
    """Advance the conversation by one turn.

    ``chosen`` carries an answer to the previous question — a tapped chip,
    a callback query. It is merged on top of what the conversation says,
    because an explicit tap beats an inference from prose.
    """
    locale = conversation.locale or "fr"
    french = str(locale).startswith("fr")

    messages = _recent_messages(conversation)
    if text:
        messages.append(text)
    constraints = reading.extract(messages)

    if chosen:
        override = reading.Constraints(
            time_slot=chosen.get("time_slot"),
            band=chosen.get("band"),
            category=chosen.get("category"),
            area=chosen.get("area"),
            budget_max=int(chosen["budget"]) if str(chosen.get("budget", "")).isdigit() else None,
            free_only=chosen.get("budget") == "free" or bool(chosen.get("free_only")),
        )
        constraints = constraints.merge(override)

    # Ask for the window and the category before searching — without a window
    # there is no valid query at all, and without a category "surprise me" is
    # a choice the user should make rather than one made for them.
    still_missing = reading.required(constraints)
    if still_missing:
        question = reading.question_chips(still_missing[0], locale=locale)
        return Reply(
            text=question["question"],
            question=question,
            state=constraints.as_dict(),
        )

    found = search.candidates(
        time_slot=constraints.time_slot,
        band=constraints.band,
        category=constraints.category,
        free_only=constraints.free_only,
    )

    # One optional narrowing question, only when the field is still wide.
    narrowing = reading.optional(constraints, candidate_count=len(found))
    if narrowing:
        question = reading.question_chips(narrowing[0], locale=locale)
        return Reply(
            text=question["question"],
            question=question,
            state=constraints.as_dict(),
        )

    if constraints.area:
        narrowed = [
            event
            for event in found
            if constraints.area.lower()
            in f"{event.get('formatted_address', '')} {event.get('venue_name', '')}".lower()
        ]
        # Never let a filter empty the answer — a worse-matching pick beats
        # "rien trouvé" when the catalog clearly has something for tonight.
        found = narrowed or found

    tastes = _consenting_tastes(conversation, constraints)
    picks = ranking.choose(
        found, tastes, locale=locale, private=not conversation.is_group
    )

    # A chip with nothing behind it must never dead-end the conversation. The
    # catalog almost always has *something* in the window, so widen to the
    # ranked feed and say plainly that this is not what was asked for — a
    # worse-matching pick the user can refuse beats "rien trouvé" while three
    # thousand events sit there.
    widened = False
    if not picks and constraints.category not in (None, "", "surprise"):
        fallback = search.candidates(
            time_slot=constraints.time_slot,
            band=constraints.band,
            category="surprise",
            free_only=constraints.free_only,
        )
        picks = ranking.choose(
            fallback, tastes, locale=locale, private=not conversation.is_group
        )
        widened = bool(picks)

    if not picks:
        slot = slots.get(constraints.time_slot)
        when = slot.label(locale).lower() if slot else ""
        return Reply(
            text=(
                f"Je ne trouve rien {when}. On essaie un autre moment ?"
                if french
                else f"I can't find anything {when}. Try another time?"
            ),
            state=constraints.as_dict(),
        )

    public = [_public_pick(event) for event in picks]
    pick_set = PickSet.objects.create(
        conversation=conversation,
        time_slot=constraints.time_slot or "",
        category=constraints.category or "",
        picks=public,
    )

    suggest_connect = _should_nudge(conversation, tastes)
    if suggest_connect:
        conversation.connect_nudged_at = timezone.now()
        conversation.save(update_fields=["connect_nudged_at"])

    reply = Reply(
        text=_headline(constraints, len(public), locale=locale, widened=widened),
        picks=public,
        share_id=pick_set.share_id,
        map_url=f"{settings.MAJSQ_WEB_URL}/m/{pick_set.share_id}",
        state=constraints.as_dict(),
        suggest_connect=suggest_connect,
        poll=_poll(public, locale=locale) if conversation.is_group else None,
    )

    Turn.objects.create(
        conversation=conversation,
        role=Turn.Role.AGENT,
        text=reply.text,
        state=constraints.as_dict(),
    )
    return reply


def _headline(constraints, count: int, *, locale: str = "fr", widened: bool = False) -> str:
    french = str(locale).startswith("fr")
    category = categories.get(constraints.category)
    slot = slots.get(constraints.time_slot)
    what = category.blurb if category else ("des idées" if french else "some ideas")
    when = slot.label(locale).lower() if slot else ("ce soir" if french else "tonight")

    if widened:
        # Say what happened. Quietly serving something else would make the
        # agent look like it ignored the question.
        label = category.label(locale).lower() if category else ""
        if french:
            return f"Rien en {label} {when}, mais il y a ça :"
        return f"Nothing in {label} {when}, but here's what's on:"

    if french:
        return f"{count} idées pour {what} {when} :"
    return f"{count} picks for {when}:"


def _poll(picks: list[dict], *, locale: str = "fr") -> dict:
    french = str(locale).startswith("fr")
    return {
        "question": "On fait lequel ?" if french else "Which one?",
        "options": [pick["title"][:100] for pick in picks],
    }
