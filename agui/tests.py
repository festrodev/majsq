"""Focused tests for the AG-UI streaming transport."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from brain.engine import Reply


class AguiRunTests(TestCase):
    def _post(self, payload: dict, **headers):
        return self.client.post(
            "/agui/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_ACCEPT="text/event-stream",
            **headers,
        )

    @staticmethod
    def _events(response) -> list[dict]:
        body = b"".join(response.streaming_content).decode()
        return [
            json.loads(line.removeprefix("data: "))
            for line in body.splitlines()
            if line.startswith("data: ")
        ]

    @override_settings(MAJSQ_SERVICE_SECRET="required", MAJSQ_OPEN_AGUI=False)
    def test_requires_service_secret(self):
        response = self._post(self._payload())

        self.assertEqual(response.status_code, 403)

    @override_settings(MAJSQ_SERVICE_SECRET="", MAJSQ_OPEN_AGUI=True)
    @patch("agui.views.engine.respond")
    def test_streams_reply_and_shared_state(self, respond):
        respond.return_value = Reply(
            text="Vous avez envie de quoi ?",
            question={
                "name": "category",
                "question": "Vous avez envie de quoi ?",
                "options": [{"value": "theatre", "label": "🎭 Théâtre"}],
            },
            state={
                "time_slot": "tonight",
                "band": "evening",
                "category": None,
                "area": None,
                "budget_max": None,
                "free_only": False,
                "party_size": 3,
            },
        )

        response = self._post(self._payload())
        events = self._events(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(
            [event["type"] for event in events],
            [
                "RUN_STARTED",
                "TEXT_MESSAGE_START",
                "TEXT_MESSAGE_CONTENT",
                "TEXT_MESSAGE_END",
                "STATE_SNAPSHOT",
                "RUN_FINISHED",
            ],
        )
        self.assertEqual(events[2]["delta"], "Vous avez envie de quoi ?")
        self.assertEqual(
            events[4]["snapshot"],
            {
                "time_slot": "tonight",
                "band": "evening",
                "category": None,
                "constraints": {
                    "area": None,
                    "budget_max": None,
                    "free_only": False,
                    "party_size": 3,
                },
                "question": respond.return_value.question,
                "picks": [],
                "share_id": "",
                "map_url": "",
                "suggest_connect": False,
            },
        )

        kwargs = respond.call_args.kwargs
        self.assertEqual(kwargs["conversation"].external_id, "web-session-1")
        self.assertEqual(kwargs["text"], "quoi faire ce soir ?")
        self.assertEqual(kwargs["chosen"], {"category": "theatre"})

    @staticmethod
    def _payload() -> dict:
        return {
            "threadId": "web-session-1",
            "runId": "run-1",
            "messages": [
                {
                    "id": "message-1",
                    "role": "user",
                    "content": "quoi faire ce soir ?",
                }
            ],
            "tools": [],
            "context": [],
            "state": {"chosen": {"category": "theatre"}},
            "forwardedProps": {},
        }
