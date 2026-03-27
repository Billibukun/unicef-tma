from django.urls import path

from . import views

app_name = "dm"

urlpatterns = [
    path("", views.dm_dashboard, name="dashboard"),
    path("participants/", views.dm_participants, name="participants"),
    path("participants/<int:assignment_id>/", views.dm_participant_profile, name="participant_profile"),
    path("participants/<int:assignment_id>/attendance/", views.dm_toggle_attendance, name="toggle_attendance"),
    path("participants/<int:assignment_id>/send-link/", views.dm_send_edit_link, name="send_edit_link"),
    path("devices/", views.dm_devices, name="devices"),
    path("devices/scan/", views.dm_scan, name="scan"),
    path("devices/<int:pk>/", views.dm_device_detail, name="device_detail"),
    path("devices/<int:pk>/assign/", views.dm_device_assign, name="device_assign"),
]
