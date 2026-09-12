from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"ok": True, "service": "majsq-agent"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    # AG-UI transport — what CopilotKit's runtime talks to.
    path("agui/", include("agui.urls")),
    # Telegram transport — same brain, different surface.
    path("tg/", include("bot.urls")),
]
