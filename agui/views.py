"""AG-UI transport — placeholder until the streaming endpoint lands.

CopilotKit's runtime registers this URL as a remote agent and POSTs a
``RunAgentInput``, expecting a Server-Sent Events stream back. Until that is
wired, the route answers with a clear 501 rather than a 404, so a misconfigured
web app says *what* is missing instead of looking like a bad URL.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def run(request):
    return JsonResponse(
        {
            "detail": "AG-UI streaming endpoint not implemented yet. "
            "The web app can drive the agent through POST /api/turn/ meanwhile.",
        },
        status=501,
    )
