"""Run a category against the catalog and return candidate events.

One place owns the merge, because a category is several catalog calls and
callers must never see the seams: duplicates across strategies, events outside
the requested band, or events that already started.
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.utils import timezone

from brain import categories, slots
from festro import client

logger = logging.getLogger(__name__)


def _started_already(event: dict, *, grace_minutes: int = 30) -> bool:
    """Has this event already begun?

    Festro's window filters answer "is it in the requested day", not "is it
    still ahead". At 21:00 a 19:00 show is the wrong pick, so it is dropped —
    with a short grace so a just-started show still shows up while it is
    realistically joinable. Unknown start times are kept.
    """
    raw = event.get("start_datetime")
    if not raw:
        return False
    try:
        start = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    return start < timezone.now() - timezone.timedelta(minutes=grace_minutes)


def candidates(
    *,
    time_slot: str | None,
    band: str | None = None,
    category: str | None = None,
    free_only: bool = False,
    limit: int = 40,
) -> list[dict]:
    """Candidate events for a slot + category, merged and de-duplicated."""
    slot = slots.get(time_slot)
    when = slot.when if slot else "today"

    seen: dict[str, dict] = {}
    for query in categories.build_queries(category):
        try:
            found = client.search_events(
                when=when,
                q=query.q,
                tags=query.tags,
                price=query.price or ("free" if free_only else None),
                limit=limit,
            )
        except Exception:  # never let one strategy break the whole answer
            logger.exception("search strategy failed: %s", query)
            continue
        for event in found:
            key = event.get("short_id")
            if key and key not in seen:
                seen[key] = event

    events = [
        event
        for event in seen.values()
        if slots.in_band(event.get("start_datetime"), band) and not _started_already(event)
    ]
    events.sort(key=lambda e: str(e.get("start_datetime") or ""))
    return events


def category_counts(*, time_slot: str | None, band: str | None = None) -> dict[str, int]:
    """How many events sit behind each chip for this window.

    Used to render counts on the chips and to hide a chip with no inventory —
    a chip that promises picks and returns none is worse than no chip.
    """
    counts: dict[str, int] = {}
    for category in categories.CATEGORIES:
        if category.key == "surprise":
            continue
        found = candidates(time_slot=time_slot, band=band, category=category.key, limit=40)
        counts[category.key] = len(found)
    return counts
