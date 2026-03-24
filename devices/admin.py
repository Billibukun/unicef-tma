from django.contrib import admin

from devices.models import Device, DeviceLog


class DeviceLogInline(admin.TabularInline):
    model = DeviceLog
    extra = 0
    readonly_fields = ["created_at", "created_by"]


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["serial_number", "imei_1", "device_type", "brand", "status", "condition", "assigned_to", "state"]
    list_filter = ["device_type", "status", "condition", "state"]
    search_fields = ["serial_number", "imei_1", "imei_2", "brand"]
    inlines = [DeviceLogInline]


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ["device", "status", "condition", "note", "created_by", "created_at"]
    list_filter = ["status", "condition"]
