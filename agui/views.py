"""AG-UI transport for the web surface."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from uuid import uuid4

from ag_ui.core import (
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder import EventEncoder
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError
from rest_framework.exceptions import AuthenticationFailed

from api.auth import require_service
from api.views import _resolve
from brain import engine
from core.models import Turn

logger = logging.getLogger(__name__)


def _last_user_text(run_input: RunAgentInput) -> str:
    """Return the last plain-text user message CopilotKit sent."""
    for message in reversed(run_input.messages):
        if message.role == "user" and isinstance(message.content, str):
            return message.content.strip()
    return ""


def _snapshot(reply: engine.Reply) -> dict:
    """Map an engine reply to the shared state documented in CONTRACT.md."""
    state = reply.state or {}
    return {
        "time_slot": state.get("time_slot"),
        "band": state.get("band"),
        "category": state.get("category"),
        "constraints": {
            "area": state.get("area"),
            "budget_max": state.get("budget_max"),
            "free_only": bool(state.get("free_only")),
            "party_size": state.get("party_size"),
        },
        "question": reply.question,
        "picks": reply.picks,
        "share_id": reply.share_id,
        "map_url": reply.map_url,
        "suggest_connect": reply.suggest_connect,
    }


def _event_stream(run_input: RunAgentInput, encoder: EventEncoder) -> Iterator[str]:
    """Run the existing brain once and encode its reply as AG-UI SSE events."""
    yield encoder.encode(RunStartedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id))

    try:
        identity = {
            "channel": "web",
            "kind": "web",
            "conversation_id": run_input.thread_id,
            "participant_id": run_input.thread_id,
            "locale": "fr",
        }
        conversation, participant, _ = _resolve(identity)
        text = _last_user_text(run_input)
        if text:
            Turn.objects.create(
                conversation=conversation,
                participant=participant,
                role=Turn.Role.USER,
                text=text,
            )

        incoming_state = run_input.state if isinstance(run_input.state, dict) else {}
        reply = engine.respond(
            conversation=conversation,
            text=text,
            chosen=incoming_state.get("chosen") or None,
        )

        message_id = str(uuid4())
        yield encoder.encode(TextMessageStartEvent(message_id=message_id))
        yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=reply.text))
        yield encoder.encode(TextMessageEndEvent(message_id=message_id))
        yield encoder.encode(StateSnapshotEvent(snapshot=_snapshot(reply)))
        yield encoder.encode(
            RunFinishedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id)
        )
    except Exception:
        logger.exception("AG-UI run failed")
        yield encoder.encode(RunErrorEvent(message="Agent run failed.", code="agent_error"))


@csrf_exempt
def run(request):
    """Accept an AG-UI RunAgentInput and stream the existing brain's reply."""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        require_service(request)
    except AuthenticationFailed as exc:
        return JsonResponse({"detail": str(exc.detail)}, status=403)

    try:
        run_input = RunAgentInput.model_validate_json(request.body)
    except (ValidationError, ValueError):
        return JsonResponse({"detail": "Invalid AG-UI request."}, status=400)

    encoder = EventEncoder(accept=request.headers.get("Accept"))
    response = StreamingHttpResponse(
        _event_stream(run_input, encoder),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
