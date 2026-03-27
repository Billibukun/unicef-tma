from django.urls import path

from . import views

urlpatterns = [
    path("", views.device_list, name="device_list"),
    path("create/", views.device_create, name="device_create"),
    path("scan/", views.device_scan, name="device_scan"),
    path("save-scanned/", views.device_save_scanned, name="device_save_scanned"),
    path("bulk-upload/", views.device_bulk_upload, name="device_bulk_upload"),
    path("<int:pk>/", views.device_detail, name="device_detail"),
    path("<int:pk>/edit/", views.device_edit, name="device_edit"),
    path("<int:pk>/assign/", views.device_assign, name="device_assign"),
    path("<int:pk>/update-status/", views.device_update_status, name="device_update_status"),
    path("<int:pk>/fix-serial/", views.device_fix_serial, name="device_fix_serial"),
    path("search/", views.device_search, name="device_search"),
    path("search-participant/", views.device_search_participant, name="device_search_participant"),
]
