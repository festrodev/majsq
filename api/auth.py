"""Service authentication for the agent's HTTP API.

Every caller is another one of our own services — the Telegram bot, the web
app's server. None of them is a browser, so this is a shared secret in a
header rather than anything user-facing. The browser never holds it: the web
app's route handlers add it server-side.
"""

from __future__ import annotations

import hmac

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

HEADER = "X-Majsq-Service-Secret"


def require_service(request) -> None:
    """Raise unless the caller proved it is one of our services."""
    expected = settings.MAJSQ_SERVICE_SECRET
    if not expected:
        # No secret configured: allowed only when explicitly opened for local
        # development, never by accident in a deployed environment.
        if settings.MAJSQ_OPEN_AGUI:
            return
        raise AuthenticationFailed(
            "MAJSQ_SERVICE_SECRET is not set. Set it, or set MAJSQ_OPEN_AGUI=1 for local dev."
        )
    provided = request.headers.get(HEADER, "")
    if not provided or not hmac.compare_digest(provided, expected):
        raise AuthenticationFailed("Bad or missing service secret.")
