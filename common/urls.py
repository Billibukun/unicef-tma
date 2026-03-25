from django.urls import path

from common import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("admin-tools/", views.admin_tools, name="admin_tools"),
    path("settings/", views.settings_view, name="settings"),
    path("admin-tools/add-user/", views.admin_add_user, name="admin_add_user"),
]
