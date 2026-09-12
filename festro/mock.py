"""Offline catalog, so a fork runs with no credentials and no network.

The fixtures are real Festro events captured on 2026-09-12 with the image
fields removed. Filtering here is deliberately approximate — it exists so the
flow can be demonstrated and tested, not to reimplement Festro's query
semantics. ``FESTRO_MOCK=1`` turns it on.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import lru_cache

from django.conf import settings
from django.utils import timezone


@lru_cache(maxsize=1)
def _events() -> list[dict]:
    path = settings.FESTRO_FIXTURES / "events.sample.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["results"]


@lru_cache(maxsize=1)
def list_tags() -> list[dict]:
    path = settings.FESTRO_FIXTURES / "tags.sample.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["results"]


def _shifted(event: dict, offset_days: int) -> dict:
    """Re-date a fixture event onto the current week.

    The fixtures were captured on a fixed day, so without this every event is
    in the past and the demo shows nothing. The shift keeps each event's time
    of day and relative order.
    """
    out = dict(event)
    for key in ("start_datetime", "end_datetime"):
        raw = event.get(key)
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        out[key] = (parsed + timedelta(days=offset_days)).isoformat()
    return out


def _public(event: dict) -> dict:
    out = dict(event)
    out["url"] = f"{settings.FESTRO_SITE_BASE}/e/{event.get('short_id', '')}"
    return out


def search_events(
    *,
    when: str | None = None,
    days: int | None = None,
    q: str | None = None,
    tags: str | None = None,
    price: str | None = None,
    limit: int = 24,
) -> list[dict]:
    captured = datetime(2026, 9, 12, tzinfo=timezone.get_current_timezone())
    offset = (timezone.localtime().date() - captured.date()).days

    rows = [_public(_shifted(event, offset)) for event in _events()]

    if tags:
        needle = tags.strip().lower()
        rows = [r for r in rows if any(needle == str(t).lower() for t in (r.get("tags") or []))]
    if q:
        needle = q.strip().lower()
        rows = [
            r
            for r in rows
            if needle
            in f"{r.get('title','')} {r.get('venue_name','')} {r.get('organizer_name','')}".lower()
        ]
    if price == "free":
        rows = [r for r in rows if r.get("is_free")]

    rows.sort(key=lambda r: str(r.get("start_datetime") or ""))
    return rows[:limit]


def profile() -> dict:
    """A stand-in taste profile, so the personalization path is demonstrable.

    Clearly fake on purpose — it is a fixture, not anyone's real history. Its
    key set matches the live endpoint exactly (pinned there by
    ProfilePayloadTests): a fixture that carries a field the real payload does
    not is how code gets written against something that never arrives.
    """
    return {
        "display_name": "Demo member",
        "taste": {
            "tags": [
                {"tag": "Electronic", "weight": 9},
                {"tag": "Rock", "weight": 4},
                {"tag": "Jazz", "weight": 2},
            ],
            "organizers": [{"slug": "newspeak", "name": "Newspeak", "weight": 6}],
            "venues": [{"name": "Bar Le Ritz PDB", "weight": 3}],
            "price_band": "under_30",
            "usual_nights": ["friday", "saturday"],
        },
        "counts": {
            "window_days": 365,
            "saved": 12,
            "reservations": 3,
            "following_at_least": 4,
        },
    }
