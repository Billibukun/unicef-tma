from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "channel", "state", "lga", "is_active"]
    list_filter = ["channel", "groups", "is_active", "state"]
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("channel", "state", "lga", "phone")}),
    )
