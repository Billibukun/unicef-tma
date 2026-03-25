from django.urls import path

from . import views

urlpatterns = [
    path("", views.training_list, name="training_list"),
    path("create/", views.training_create, name="training_create"),
    path("<int:pk>/", views.training_detail, name="training_detail"),
    path("<int:pk>/edit/", views.training_edit, name="training_edit"),
    path("<int:pk>/delete/", views.training_delete, name="training_delete"),
    # Inline management (HTMX)
    path("<int:pk>/add-category/", views.add_category, name="training_add_category"),
    path("<int:pk>/add-cluster/", views.add_cluster, name="training_add_cluster"),
    path("category/<int:cat_id>/toggle/", views.toggle_category_registration, name="toggle_category_registration"),
    path("category/<int:cat_id>/edit/", views.edit_category, name="edit_category"),
    path("category/<int:cat_id>/delete/", views.delete_category, name="delete_category"),
    path("cluster/<int:cluster_id>/delete/", views.delete_cluster, name="delete_cluster"),
    path("cluster/<int:cluster_id>/edit/", views.edit_cluster, name="edit_cluster"),
    path("cluster/<int:cluster_id>/update-lgas/", views.update_cluster_lgas, name="update_cluster_lgas"),
    path("assignment/<int:assignment_id>/", views.assignment_detail, name="training_assignment_detail"),
    path("assignment/<int:assignment_id>/edit/", views.edit_assignment, name="training_edit_assignment"),
    path("<int:pk>/add-level/", views.add_level, name="training_add_level"),
    path("level/<int:level_id>/delete/", views.delete_level, name="delete_level"),
    path("<int:pk>/search-participants/", views.search_participants_for_training, name="training_search_participants"),
    path("<int:pk>/assign-participant/", views.assign_participant_to_training, name="training_assign_participant"),
    path("assignment/<int:assignment_id>/remove/", views.remove_assignment, name="training_remove_assignment"),
    path("<int:pk>/search-managers/", views.search_managers, name="training_search_managers"),
    path("<int:pk>/add-manager/", views.add_manager, name="training_add_manager"),
    path("<int:pk>/remove-manager/<int:user_id>/", views.remove_manager, name="training_remove_manager"),
    path("<int:pk>/toggle-devices/", views.toggle_devices, name="training_toggle_devices"),
    path("<int:pk>/save-settings/", views.save_training_settings, name="training_save_settings"),
]
