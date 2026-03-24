from django.contrib import admin

from participants.models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ["full_name", "channel", "channel_role", "state", "lga", "email"]
    list_filter = ["channel", "channel_role", "state"]
    search_fields = ["first_name", "last_name", "email", "phone"]
