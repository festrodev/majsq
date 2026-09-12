"""Focused tests for the agent HTTP contract."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.models import FestroLink
from festro.client import FestroError


@override_settings(MAJSQ_SERVICE_SECRET="service-secret", MAJSQ_OPEN_AGUI=False)
class LinkTests(TestCase):
    def _post(self, payload: dict, *, authenticated: bool = True):
        headers = {}
        if authenticated:
            headers["HTTP_X_MAJSQ_SERVICE_SECRET"] = "service-secret"
        return self.client.post(
            "/api/link/",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    @staticmethod
    def _payload() -> dict:
        return {
            "channel": "telegram",
            "kind": "dm",
            "conversation_id": "100",
            "participant_id": "42",
            "display_name": "Selene",
            "code": "fcg_once",
            "code_verifier": "verifier",
            "redirect_uri": "https://majsq.festro.com/connect/callback",
        }

    def test_requires_service_secret(self):
        response = self._post(self._payload(), authenticated=False)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(FestroLink.objects.exists())

    def test_requires_every_exchange_field(self):
        payload = self._payload()
        del payload["code_verifier"]

        response = self._post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "code_verifier is required"})
        self.assertFalse(FestroLink.objects.exists())

    @patch("api.views.exchange_connect_code")
    def test_exchanges_and_stores_credential(self, exchange):
        exchange.return_value = {
            "credential": "fcc_profile_only",
            "display_name": "Selene F.",
            "expires_at": "2026-12-11T15:00:00Z",
        }

        response = self._post(self._payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"connected": True, "display_name": "Selene F."}
        )
        link = FestroLink.objects.get()
        self.assertEqual(link.participant.channel, "telegram")
        self.assertEqual(link.participant.external_id, "42")
        self.assertEqual(link.credential, "fcc_profile_only")
        self.assertEqual(link.festro_display_name, "Selene F.")
        self.assertIsNone(link.revoked_at)
        exchange.assert_called_once_with(
            code="fcg_once",
            code_verifier="verifier",
            redirect_uri="https://majsq.festro.com/connect/callback",
        )

    @patch("api.views.exchange_connect_code")
    def test_does_not_store_link_when_exchange_fails(self, exchange):
        exchange.side_effect = FestroError("POST /api/v1/connect/token/ returned 400")

        response = self._post(self._payload())

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "Festro connection failed."})
        self.assertFalse(FestroLink.objects.exists())
