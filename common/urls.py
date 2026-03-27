from django.urls import path

from common import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("admin-tools/", views.admin_tools, name="admin_tools"),
    path("settings/", views.settings_view, name="settings"),
    path("admin-tools/add-user/", views.admin_add_user, name="admin_add_user"),
    path("admin-tools/users/", views.admin_users_page, name="admin_users"),
    path("admin-tools/channels/", views.admin_channels_page, name="admin_channels"),
    path("lgas/", views.lgas_json, name="lgas_json"),
    path("admin-tools/upload-lgas/", views.upload_lgas, name="admin_upload_lgas"),
    path("admin-tools/reset-password/<int:user_id>/", views.admin_reset_password, name="admin_reset_password"),
    path("admin-tools/edit-user/<int:user_id>/", views.admin_edit_user, name="admin_edit_user"),
    path("admin-tools/toggle-user/<int:user_id>/", views.admin_toggle_user, name="admin_toggle_user"),
]
