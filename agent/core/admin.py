from django.contrib import admin

from core.models import Conversation, FestroLink, Membership, Participant, PickSet, Turn


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "external_id", "title", "last_active_at")
    list_filter = ("kind",)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "display_name", "external_id")
    list_filter = ("channel",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "participant", "use_my_taste")
    list_filter = ("use_my_taste",)


@admin.register(FestroLink)
class FestroLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "participant", "festro_display_name", "connected_at", "revoked_at")


@admin.register(Turn)
class TurnAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role",)


@admin.register(PickSet)
class PickSetAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "share_id", "category", "time_slot", "created_at")
