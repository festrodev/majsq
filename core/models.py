"""The conversation store.

Two rules shape every model here, both from the design review:

1. **Identity is never taken from the client.** A ``Participant`` is created
   from a verified Telegram update or from the web session cookie, never from a
   field in a request body. See ``core.identity``.
2. **A Festro link made in a DM does not disclose anything in a group.** The
   link lives on the participant; permission to *use* it lives on the
   per-group ``Membership``, and is read on every turn before any cached
   profile is consulted.
"""

from __future__ import annotations

import secrets

from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """One chat: a Telegram DM, a Telegram group, or a web session."""

    class Kind(models.TextChoices):
        DM = "dm", "Telegram DM"
        GROUP = "group", "Telegram group"
        WEB = "web", "Web chat"

    kind = models.CharField(max_length=8, choices=Kind.choices)
    # Telegram chat id, or the web session id. Unique per kind.
    external_id = models.CharField(max_length=128)
    title = models.CharField(max_length=200, blank=True, default="")
    locale = models.CharField(max_length=8, default="fr")
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    # When the connect nudge was last shown, so it is offered at most daily.
    connect_nudged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "external_id"], name="uniq_conversation_kind_external"
            )
        ]
        indexes = [models.Index(fields=["last_active_at"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.external_id}"

    @property
    def is_group(self) -> bool:
        return self.kind == self.Kind.GROUP


class Participant(models.Model):
    """A person, as seen by one transport.

    The same human in Telegram and on the web is two rows until they connect
    the same Festro account; that is deliberate — we have no way to prove they
    are the same person before then, and guessing would be a disclosure bug.
    """

    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WEB = "web", "Web"

    channel = models.CharField(max_length=10, choices=Channel.choices)
    # Telegram user id, or the web session id from the httpOnly cookie.
    external_id = models.CharField(max_length=128)
    display_name = models.CharField(max_length=120, blank=True, default="")
    locale = models.CharField(max_length=8, default="fr")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "external_id"], name="uniq_participant_channel_external"
            )
        ]

    def __str__(self) -> str:
        return self.display_name or f"{self.channel}:{self.external_id}"


class Membership(models.Model):
    """A participant in a conversation, and what they consented to there.

    ``use_my_taste`` is the per-group consent from the review: persistent,
    reversible, and checked on every turn *before* any cached profile is used,
    so switching it off excludes the member on the next turn even while their
    profile is still warm in the cache. It says nothing about attendance — the
    poll is what says who is coming.
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="memberships"
    )
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="memberships"
    )
    use_my_taste = models.BooleanField(default=False)
    taste_consent_changed_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "participant"], name="uniq_membership")
        ]

    def set_taste_consent(self, *, enabled: bool) -> None:
        self.use_my_taste = enabled
        self.taste_consent_changed_at = timezone.now()
        self.save(update_fields=["use_my_taste", "taste_consent_changed_at"])

    def __str__(self) -> str:
        return f"{self.participant} in {self.conversation}"


class FestroLink(models.Model):
    """A participant's connected Festro account.

    Holds the opaque ``ConnectedCredential`` key issued by Festro's connect
    flow — NOT a Festro device token. It is accepted by exactly one endpoint
    (``GET /api/v1/connect/profile/``) and carries no account authority.
    """

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="festro_link"
    )
    # Opaque credential. Encrypt at rest before this stores a real one in a
    # deployed environment; a hackathon laptop keeps it in the local database.
    credential = models.CharField(max_length=255)
    festro_display_name = models.CharField(max_length=120, blank=True, default="")
    connected_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_live(self) -> bool:
        if self.revoked_at:
            return False
        return not (self.expires_at and self.expires_at <= timezone.now())

    def __str__(self) -> str:
        return f"Festro link for {self.participant}"


class ConnectState(models.Model):
    """A pending connect handshake, bound to the initiating identity.

    Created when someone taps "Connect Festro", consumed once when Festro
    redirects back. Binding the state to the participant is what stops a
    bearer link from attaching someone else's account.
    """

    state = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="connect_states"
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)
    code_verifier = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"connect state for {self.participant}"


class Turn(models.Model):
    """One message in a conversation, in the order it happened."""

    class Role(models.TextChoices):
        USER = "user", "User"
        AGENT = "agent", "Agent"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="turns")
    participant = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="turns"
    )
    role = models.CharField(max_length=8, choices=Role.choices)
    text = models.TextField(blank=True, default="")
    # What the agent understood at this turn: time_slot, category, constraints.
    state = models.JSONField(default=dict, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self) -> str:
        return f"{self.role}: {self.text[:40]}"


def _share_id() -> str:
    """Unguessable id for a map share page (~128 bits)."""
    return secrets.token_urlsafe(16)


class PickSet(models.Model):
    """The three picks from one turn, and the public snapshot the map renders.

    ``picks`` holds ONLY public event fields — title, when, venue, coordinates,
    price label, festro.com link. Never a member's history, never a reason
    naming a person, never a signed image URL. Anyone with the ``share_id``
    can open the map page, so what is in here is what is public.
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="pick_sets"
    )
    share_id = models.CharField(max_length=32, unique=True, default=_share_id)
    time_slot = models.CharField(max_length=40, blank=True, default="")
    category = models.CharField(max_length=60, blank=True, default="")
    picks = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{len(self.picks)} picks · {self.share_id}"
