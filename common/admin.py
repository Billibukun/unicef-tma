from django.contrib import admin

from common.models import Channel, LGA, ParticipantCategory, State, TrainingRole


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_editable = ["is_active"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name"]


@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ["name", "state"]
    list_filter = ["state"]
    search_fields = ["name"]


@admin.register(TrainingRole)
class TrainingRoleAdmin(admin.ModelAdmin):
    list_display = ["name", "channel"]
    list_filter = ["channel"]


@admin.register(ParticipantCategory)
class ParticipantCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "daily_rate", "default_days", "description"]
    list_editable = ["daily_rate", "default_days"]
