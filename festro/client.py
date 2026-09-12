"""The only place that talks to Festro.

Three endpoints, all read-only:

* ``GET /api/v1/events/``          — the public catalog (anonymous)
* ``GET /api/v1/tags/``            — the tag taxonomy behind the category chips
* ``GET /api/v1/connect/profile/`` — one member's minimized taste profile,
  with their opaque connect credential

The connect handoff also makes one write-like exchange call:

* ``POST /api/v1/connect/token/``  — consume a short-lived authorization code
  and receive the profile-only credential

Rules that live here because they are easy to break elsewhere:

* Every request carries a ``User-Agent`` that names this project, so a noisy
  fork can be rate-limited without touching real Festro users.
* Searches are cached for ``FESTRO_CACHE_SECONDS`` — a group poll with five
  reactions must not re-query the catalog five times. The anonymous throttle
  is 60 requests per minute per IP.
* Image URLs are dropped on the way in. Festro serves signed, expiring URLs
  and the artwork is licensed for Festro's own pages; maj$q sends text and
  links. See ``_public_fields``.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# module-level cache: {key: (expires_at, payload)}
_CACHE: dict[str, tuple[float, Any]] = {}


class FestroError(RuntimeError):
    """A call to Festro failed. Callers degrade, they do not crash."""


def _headers() -> dict[str, str]:
    headers = {
        "User-Agent": settings.FESTRO_USER_AGENT,
        "Accept": "application/json",
    }
    # Sent only when registered. Festro's client trust gate is satisfied by
    # App Check OR these credentials; in monitor mode neither is required, but
    # sending them means maj$q keeps working when enforcement is switched on.
    if settings.FESTRO_CLIENT_ID and settings.FESTRO_CLIENT_SECRET:
        headers["X-Festro-Client-Id"] = settings.FESTRO_CLIENT_ID
        headers["X-Festro-Client-Secret"] = settings.FESTRO_CLIENT_SECRET
    return headers


def _cached(key: str):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    return None


def _store(key: str, value: Any) -> Any:
    _CACHE[key] = (time.monotonic() + settings.FESTRO_CACHE_SECONDS, value)
    return value


def _get(path: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
    url = f"{settings.FESTRO_API_BASE}{path}"
    merged = _headers()
    if headers:
        merged.update(headers)
    try:
        response = requests.get(
            url, params=params or {}, headers=merged, timeout=settings.FESTRO_TIMEOUT
        )
    except requests.RequestException as exc:
        raise FestroError(f"GET {path} failed: {exc}") from exc
    if response.status_code >= 400:
        raise FestroError(f"GET {path} returned {response.status_code}")
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise FestroError(f"GET {path} returned non-JSON") from exc


def exchange_connect_code(*, code: str, code_verifier: str, redirect_uri: str) -> dict:
    """Exchange a one-time connect grant for a profile-only credential."""
    if not settings.FESTRO_CLIENT_ID or not settings.FESTRO_CLIENT_SECRET:
        raise FestroError("Festro client credentials are not configured")

    path = "/api/v1/connect/token/"
    try:
        response = requests.post(
            f"{settings.FESTRO_API_BASE}{path}",
            json={
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
            headers=_headers(),
            timeout=settings.FESTRO_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise FestroError(f"POST {path} failed: {exc}") from exc
    if response.status_code >= 400:
        raise FestroError(f"POST {path} returned {response.status_code}")
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise FestroError(f"POST {path} returned non-JSON") from exc
    if not isinstance(payload, dict) or not payload.get("credential"):
        raise FestroError(f"POST {path} returned no credential")
    return payload


# --------------------------------------------------------------- catalog ----

# The public event fields maj$q is allowed to carry into a chat, a map share
# page, or a model prompt. Everything else — including cover_image and
# card_image, which are signed and licensed for Festro's own pages — is
# dropped here, once, rather than remembered at each call site.
_PUBLIC_FIELDS = (
    "short_id",
    "title",
    "description",
    "venue_name",
    "city",
    "formatted_address",
    "latitude",
    "longitude",
    "start_datetime",
    "start_time_known",
    "end_datetime",
    "timezone",
    "tags",
    "is_free",
    "ticketing_type",
    "organizer_name",
    "organizer_slug",
    "market",
)


def _public_fields(event: dict) -> dict:
    out = {key: event.get(key) for key in _PUBLIC_FIELDS if key in event}
    out["url"] = f"{settings.FESTRO_SITE_BASE}/e/{event.get('short_id', '')}"
    return out


def search_events(
    *,
    when: str | None = None,
    days: int | None = None,
    q: str | None = None,
    tags: str | None = None,
    price: str | None = None,
    market: str | None = None,
    limit: int = 24,
) -> list[dict]:
    """Search the public catalog. Returns public fields only, never raises.

    ``when`` accepts what Festro's Explore chips accept: ``today``,
    ``weekend``, ``next-weekend``, ``YYYY-MM-DD``, or a ``from..to`` span.
    """
    if settings.FESTRO_MOCK:
        from festro import mock

        return mock.search_events(when=when, days=days, q=q, tags=tags, price=price, limit=limit)

    params: dict[str, Any] = {
        "market": market or settings.FESTRO_MARKET,
        "ordering": "-rank_score",
        "page_size": limit,
    }
    for key, value in (("when", when), ("days", days), ("q", q), ("tags", tags), ("price", price)):
        if value:
            params[key] = value

    cache_key = "events:" + json.dumps(params, sort_keys=True)
    hit = _cached(cache_key)
    if hit is not None:
        return hit

    try:
        payload = _get("/api/v1/events/", params=params)
    except FestroError as exc:
        logger.warning("festro: search failed (%s); returning nothing", exc)
        return []

    results = payload.get("results", payload if isinstance(payload, list) else [])
    events = [_public_fields(event) for event in results]
    return _store(cache_key, events)


def list_tags(*, limit: int = 40) -> list[dict]:
    """The tag taxonomy behind the category chips."""
    if settings.FESTRO_MOCK:
        from festro import mock

        return mock.list_tags()

    hit = _cached("tags")
    if hit is not None:
        return hit
    try:
        payload = _get("/api/v1/tags/", params={"page_size": limit})
    except FestroError as exc:
        logger.warning("festro: tags failed (%s); using the built-in list", exc)
        from festro import mock

        return mock.list_tags()
    results = payload.get("results", payload if isinstance(payload, list) else [])
    return _store("tags", results)


# --------------------------------------------------------------- profile ----


def fetch_profile(credential: str) -> dict | None:
    """One member's minimized taste profile, or None.

    ``credential`` is the opaque key from Festro's connect flow. It is NOT a
    Festro device token: it is accepted by this endpoint alone and carries no
    account authority. A failure here degrades to "no taste data" — never to
    an error the group sees.
    """
    if not credential:
        return None
    if settings.FESTRO_MOCK:
        from festro import mock

        return mock.profile()
    try:
        return _get(
            "/api/v1/connect/profile/",
            headers={"Authorization": f"Connect {credential}"},
        )
    except FestroError as exc:
        logger.info("festro: profile unavailable (%s)", exc)
        return None
