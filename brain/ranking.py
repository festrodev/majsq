"""Pick three events from the candidates.

Ranking happens **after** the hard filters (window, band, category, budget) —
those are in ``brain.search`` and in the constraints the agent extracted. What
is left here is preference: among events that all qualify, which three does
this particular group want?

The shape comes from the design review:

    affinity_i = 0.6·tags + 0.25·organizers + 0.15·venues      (per member)
    group      = 0.7·mean(affinity) + 0.3·min(affinity)

The ``min`` term is the point of the formula: it is what stops three
metal-heads and one person who hates metal from being sent to a metal show.
A member with no taste profile contributes what they said in the chat, as a
synthetic profile, rather than a zero that would drag the minimum down and
punish the group for having a guest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

W_TAGS = 0.60
W_ORGANIZERS = 0.25
W_VENUES = 0.15

MEAN_WEIGHT = 0.70
MIN_WEIGHT = 0.30


@dataclass
class Taste:
    """One member's normalized preferences, 0..1 per key.

    ``label`` is only ever used for DM-private explanations. Group-facing
    reasons are aggregate ("2 sur 3 aiment le jazz") and never name a member.
    """

    label: str = ""
    tags: dict[str, float] = field(default_factory=dict)
    organizers: dict[str, float] = field(default_factory=dict)
    venues: dict[str, float] = field(default_factory=dict)
    synthetic: bool = False

    @classmethod
    def from_profile(cls, profile: dict, *, label: str = "") -> Taste:
        """Build from Festro's minimized connect profile payload."""
        taste = (profile or {}).get("taste", {})
        return cls(
            label=label or (profile or {}).get("display_name", ""),
            tags=_normalize({t.get("tag"): t.get("weight", 1) for t in taste.get("tags", [])}),
            organizers=_normalize(
                {o.get("slug"): o.get("weight", 1) for o in taste.get("organizers", [])}
            ),
            venues=_normalize({v.get("name"): v.get("weight", 1) for v in taste.get("venues", [])}),
        )

    @classmethod
    def from_stated(cls, *, tags: list[str], label: str = "") -> Taste:
        """Build from what someone said in the chat ("j'aime le jazz").

        Marked ``synthetic`` so reasons can say "tu as dit" rather than
        implying it came from their Festro history.
        """
        return cls(label=label, tags=_normalize(dict.fromkeys(tags, 1.0)), synthetic=True)


def _normalize(weights: dict) -> dict[str, float]:
    """Scale to 0..1 so a prolific history cannot dominate a light one."""
    clean = {
        str(key).strip().lower(): float(value) for key, value in weights.items() if key and value
    }
    if not clean:
        return {}
    top = max(clean.values())
    if top <= 0:
        return {}
    return {key: value / top for key, value in clean.items()}


def _overlap(event_values: list[str], weights: dict[str, float]) -> float:
    if not weights or not event_values:
        return 0.0
    scores = [weights.get(str(value).strip().lower(), 0.0) for value in event_values]
    return max(scores) if scores else 0.0


def affinity(event: dict, taste: Taste) -> float:
    """How much one member should like one event, 0..1."""
    tags = event.get("tags") or []
    organizer = [event.get("organizer_slug") or ""]
    venue = [event.get("venue_name") or ""]
    return (
        W_TAGS * _overlap(tags, taste.tags)
        + W_ORGANIZERS * _overlap(organizer, taste.organizers)
        + W_VENUES * _overlap(venue, taste.venues)
    )


def group_score(event: dict, tastes: list[Taste]) -> float:
    """Score one event for the whole group."""
    if not tastes:
        return 0.0
    scores = [affinity(event, taste) for taste in tastes]
    mean = sum(scores) / len(scores)
    return MEAN_WEIGHT * mean + MIN_WEIGHT * min(scores)


def reasons(event: dict, tastes: list[Taste], *, locale: str = "fr", private: bool = False) -> str:
    """Why this pick — aggregate in a group, never naming a member.

    ``private=True`` (a DM, where there is only one person to talk about) may
    name what that person likes; in a group it must not, because a link made
    in a DM must not disclose anything to the group.
    """
    if not tastes:
        return ""
    tags = [str(t).strip().lower() for t in (event.get("tags") or [])]
    if not tags:
        return ""
    liked = [taste for taste in tastes if any(tag in taste.tags for tag in tags)]
    if not liked:
        return ""
    tag_label = (event.get("tags") or [""])[0]
    if private or len(tastes) == 1:
        if str(locale).startswith("fr"):
            return f"tu aimes {tag_label}".strip()
        return f"you like {tag_label}".strip()
    if str(locale).startswith("fr"):
        return f"{len(liked)} sur {len(tastes)} aiment {tag_label}"
    return f"{len(liked)} of {len(tastes)} like {tag_label}"


def choose(
    events: list[dict],
    tastes: list[Taste],
    *,
    count: int = 3,
    locale: str = "fr",
    private: bool = False,
) -> list[dict]:
    """The three picks: highest group score, with variety enforced.

    Variety is not decoration. Three shows at the same venue read as a broken
    recommender even when each one scores well, so at most one pick per venue
    is taken on the first pass and the rule is only relaxed if that cannot
    fill the list.
    """
    if not events:
        return []
    scored = sorted(
        events,
        key=lambda event: (group_score(event, tastes), str(event.get("start_datetime") or "")),
        reverse=True,
    )

    picked: list[dict] = []
    used_venues: set[str] = set()
    used_titles: set[str] = set()

    def title_key(event: dict) -> str:
        return " ".join((event.get("title") or "").lower().split())

    for event in scored:
        venue = (event.get("venue_name") or "").strip().lower()
        if venue and venue in used_venues:
            continue
        if title_key(event) in used_titles:
            continue
        picked.append(event)
        used_venues.add(venue)
        used_titles.add(title_key(event))
        if len(picked) == count:
            break
    # Relax the venue rule only if we came up short. The title rule is never
    # relaxed: a recurring series shown twice ("Alice in Wonderland" on Friday
    # and again on Saturday) reads as a broken recommender, not as two options.
    for event in scored:
        if len(picked) >= count:
            break
        if event in picked or title_key(event) in used_titles:
            continue
        picked.append(event)
        used_titles.add(title_key(event))

    for event in picked:
        event["why"] = reasons(event, tastes, locale=locale, private=private)
        event["score"] = round(group_score(event, tastes), 3)
    return picked
