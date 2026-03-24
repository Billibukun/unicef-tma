from django.contrib import admin

from banks.models import Bank, BankAccount


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "cbn_code", "unicef_code", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["unicef_code", "is_active"]
    search_fields = ["name", "short_name", "cbn_code", "unicef_code"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["participant", "bank", "account_number", "account_name", "is_validated", "validation_method"]
    list_filter = ["is_validated", "bank"]
    search_fields = ["account_number", "account_name", "participant__first_name", "participant__last_name"]
