"""Time slots — the first question, and the only one that is always required.

Everything downstream is a catalog query, so the window has to exist before a
category means anything. A slot is a ``when`` value Festro's Explore chips
already understand (``today``, ``weekend``, ``YYYY-MM-DD``, ``from..to``) plus
an optional part-of-day band that filters locally on ``start_datetime`` —
Festro has no hour filter, so the band is applied here after the fetch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.utils import timezone


@dataclass(frozen=True)
class Slot:
    key: str
    label_fr: str
    label_en: str
    when: str
    emoji: str = ""

    def label(self, locale: str) -> str:
        return self.label_fr if str(locale).startswith("fr") else self.label_en


def _iso(day: date) -> str:
    return day.isoformat()


def slots(*, today: date | None = None) -> list[Slot]:
    """The slot chips, relative to today in the configured timezone."""
    today = today or timezone.localdate()
    tomorrow = today + timedelta(days=1)
    # Friday of the current week; if it is already the weekend, this weekend
    # still means the days ahead, which is what Festro's `weekend` returns.
    return [
        Slot("tonight", "Ce soir", "Tonight", "today", "🌙"),
        Slot("tomorrow", "Demain", "Tomorrow", _iso(tomorrow), "🌤"),
        Slot("weekend", "Ce week-end", "This weekend", "weekend", "🎉"),
        Slot(
            "week",
            "Cette semaine",
            "This week",
            f"{_iso(today)}..{_iso(today + timedelta(days=6))}",
            "🗓",
        ),
    ]


BY_KEY: dict[str, Slot] = {}


def get(key: str | None) -> Slot | None:
    if not key:
        return None
    key = key.strip().lower()
    for slot in slots():
        if slot.key == key:
            return slot
    # A bare date is a valid slot too: the user tapped a day in a picker.
    try:
        parsed = date.fromisoformat(key)
    except ValueError:
        return None
    return Slot(key, parsed.strftime("%A %d %B"), parsed.strftime("%A %d %B"), key)


# --------------------------------------------------------------- bands ----

# Local filtering only. Festro returns a window; these narrow it by hour.
BANDS: dict[str, tuple[int, int]] = {
    "afternoon": (11, 17),
    "evening": (17, 23),
    "late": (22, 5),  # wraps past midnight
}

BAND_LABELS = {
    "afternoon": ("Après-midi", "Afternoon"),
    "evening": ("Soirée", "Evening"),
    "late": ("Tard", "Late night"),
}


def band_labels(locale: str = "fr") -> list[dict]:
    index = 0 if str(locale).startswith("fr") else 1
    return [{"key": key, "label": labels[index]} for key, labels in BAND_LABELS.items()]


def in_band(start: datetime | str | None, band: str | None) -> bool:
    """Does an event's start fall inside a part-of-day band?

    An event with no known start time passes every band: Festro marks those
    with ``start_time_known=False`` and hiding them would silently drop real
    events from a window the user asked for.
    """
    if not band or band not in BANDS:
        return True
    if start is None:
        return True
    if isinstance(start, str):
        try:
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            return True
    hour = timezone.localtime(start).hour
    low, high = BANDS[band]
    if low <= high:
        return low <= hour < high
    # Wraps midnight: 22:00–05:00
    return hour >= low or hour < high
