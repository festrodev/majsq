from django.urls import path

from api import views

urlpatterns = [
    # The one endpoint every surface calls to advance a conversation.
    path("turn/", views.turn, name="turn"),
    # Chips a surface renders before the first turn.
    path("slots/", views.slot_chips, name="slots"),
    path("categories/", views.category_chips, name="categories"),
    # Per-group taste consent, toggled from a surface's own button.
    path("consent/", views.consent, name="consent"),
    # Exchange a short-lived Festro code and attach the resulting profile-only
    # credential to the transport-verified participant.
    path("link/", views.link, name="link"),
    # The public map share payload. No service secret: an unguessable share id
    # is the credential, and the payload is public event fields only.
    path("shares/<str:share_id>/", views.share, name="share"),
]
