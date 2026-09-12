"""The agent's HTTP API.

Identity is the thing to get right here. A surface tells us *which* transport
and *which* external id — a Telegram chat and user id, or a web session id —
and we resolve that to our own rows. What a surface may never do is hand us a
participant id of its own choosing: that would let anyone claim to be anyone,
and with connected Festro accounts in play that is a disclosure bug, not a bug
report. The service secret is what makes the transport's claim trustworthy;
see ``api.auth``.
"""

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.auth import require_service
from brain import categories as categories_module
from brain import engine, search, slots
from core.models import Conversation, FestroLink, Membership, Participant, PickSet, Turn
from festro.client import FestroError, exchange_connect_code

logger = logging.getLogger(__name__)


def _resolve(payload: dict) -> tuple[Conversation, Participant, Membership]:
    """Map a surface's (channel, external ids) to our rows, creating as needed."""
    channel = payload.get("channel", "web")
    kind = payload.get("kind") or ("web" if channel == "web" else "dm")

    conversation, _ = Conversation.objects.get_or_create(
        kind=kind,
        external_id=str(payload["conversation_id"]),
        defaults={
            "title": payload.get("title", "")[:200],
            "locale": payload.get("locale", "fr"),
        },
    )
    if payload.get("locale") and conversation.locale != payload["locale"]:
        conversation.locale = payload["locale"]
        conversation.save(update_fields=["locale"])

    participant, created = Participant.objects.get_or_create(
        channel=channel,
        external_id=str(payload["participant_id"]),
        defaults={
            "display_name": payload.get("display_name", "")[:120],
            "locale": payload.get("locale", "fr"),
        },
    )
    if not created and payload.get("display_name") and not participant.display_name:
        participant.display_name = payload["display_name"][:120]
        participant.save(update_fields=["display_name"])

    membership, _ = Membership.objects.get_or_create(
        conversation=conversation, participant=participant
    )
    return conversation, participant, membership


@api_view(["POST"])
def turn(request):
    """Advance a conversation by one turn.

    Body::

        {
          "channel": "telegram" | "web",
          "kind": "dm" | "group" | "web",
          "conversation_id": "<telegram chat id | web session id>",
          "participant_id": "<telegram user id | web session id>",
          "display_name": "Ali",
          "locale": "fr",
          "text": "quoi faire ce soir?",
          "chosen": {"time_slot": "tonight"}      // a tapped chip, optional
        }
    """
    require_service(request)
    payload = request.data or {}
    for required in ("conversation_id", "participant_id"):
        if not payload.get(required):
            return Response({"detail": f"{required} is required"}, status=400)

    conversation, participant, _ = _resolve(payload)

    text = (payload.get("text") or "").strip()
    if text:
        Turn.objects.create(
            conversation=conversation,
            participant=participant,
            role=Turn.Role.USER,
            text=text,
        )

    reply = engine.respond(
        conversation=conversation,
        text=text,
        chosen=payload.get("chosen") or None,
    )
    return Response(reply.as_dict())


@api_view(["GET"])
def slot_chips(request):
    """Time-slot chips, plus the part-of-day bands."""
    require_service(request)
    locale = request.query_params.get("locale", "fr")
    return Response(
        {
            "slots": [
                {"key": slot.key, "label": slot.label(locale), "emoji": slot.emoji}
                for slot in slots.slots()
            ],
            "bands": slots.band_labels(locale),
        }
    )


@api_view(["GET"])
def category_chips(request):
    """Category chips for a window, with live counts.

    ``?counts=1`` runs a catalog query per category — a few seconds, and worth
    it before rendering: a chip that promises picks and returns none is worse
    than no chip, so the caller hides empty ones.
    """
    require_service(request)
    locale = request.query_params.get("locale", "fr")
    chips = categories_module.chips(locale)

    if request.query_params.get("counts"):
        counts = search.category_counts(
            time_slot=request.query_params.get("time_slot", "tonight"),
            band=request.query_params.get("band") or None,
        )
        for chip in chips:
            chip["count"] = counts.get(chip["key"])
    return Response({"categories": chips})


@api_view(["POST"])
def consent(request):
    """Toggle one member's per-group taste consent.

    Persistent and reversible, and read live on every turn before any cached
    profile is used — so switching it off excludes that member on the very
    next message rather than whenever a cache happens to expire.
    """
    require_service(request)
    payload = request.data or {}
    _, _, membership = _resolve(payload)
    enabled = bool(payload.get("use_my_taste"))
    membership.set_taste_consent(enabled=enabled)
    return Response({"use_my_taste": membership.use_my_taste})


@api_view(["POST"])
def link(request):
    """Finish a Festro connect handoff for a transport-verified participant."""
    require_service(request)
    payload = request.data or {}
    required_fields = (
        "conversation_id",
        "participant_id",
        "code",
        "code_verifier",
        "redirect_uri",
    )
    for required in required_fields:
        if not payload.get(required):
            return Response({"detail": f"{required} is required"}, status=400)

    _, participant, _ = _resolve(payload)
    try:
        result = exchange_connect_code(
            code=str(payload["code"]),
            code_verifier=str(payload["code_verifier"]),
            redirect_uri=str(payload["redirect_uri"]),
        )
    except FestroError as exc:
        logger.info("festro: connect exchange unavailable (%s)", exc)
        return Response({"detail": "Festro connection failed."}, status=502)

    expires_at = None
    if result.get("expires_at"):
        expires_at = parse_datetime(str(result["expires_at"]))

    display_name = str(result.get("display_name") or "")[:120]
    FestroLink.objects.update_or_create(
        participant=participant,
        defaults={
            "credential": str(result["credential"]),
            "festro_display_name": display_name,
            "connected_at": timezone.now(),
            "expires_at": expires_at,
            "revoked_at": None,
        },
    )
    return Response({"connected": True, "display_name": display_name})


@api_view(["GET"])
def share(request, share_id: str):
    """The public payload behind a map link.

    Deliberately unauthenticated: the unguessable id *is* the credential, and
    the stored payload is public event fields only — no conversation history,
    no member reasons, no signed image URLs. Anyone the group forwards the
    link to can open the map, which is the point.
    """
    pick_set = get_object_or_404(PickSet, share_id=share_id)
    return Response(
        {
            "share_id": pick_set.share_id,
            "time_slot": pick_set.time_slot,
            "category": pick_set.category,
            "picks": pick_set.picks,
            "created_at": pick_set.created_at,
        }
    )
