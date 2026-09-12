from django.urls import path

from agui import views

urlpatterns = [
    # CopilotKit's runtime streams from here. One POST, SSE response.
    path("", views.run, name="agui-run"),
]
