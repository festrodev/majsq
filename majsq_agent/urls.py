from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"ok": True, "service": "majsq-agent"})


urlpatterns = [
    # Both spellings on purpose. Google's front end intercepts a bare
    # "/healthz" on *.run.app and answers its own 404 before the request ever
    # reaches the container — the deploy workflow's health check failed on a
    # service that was in fact running perfectly. "/healthz/" gets through.
    path("healthz", healthz, name="healthz"),
    path("healthz/", healthz, name="healthz-slash"),
    path("admin/", admin.site.urls),
    # The HTTP contract every surface calls. majsqbot and majsqweb are both
    # clients of this; neither holds the model key or talks to Festro directly.
    path("api/", include("api.urls")),
    # AG-UI transport — what CopilotKit's runtime streams from.
    path("agui/", include("agui.urls")),
]
