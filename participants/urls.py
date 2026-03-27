from django.urls import path

from participants import views

urlpatterns = [
    path("", views.participant_list, name="participant_list"),
    path("create/", views.participant_create, name="participant_create"),
    path("import/", views.participant_import, name="participant_import"),
    path("export/", views.participant_export, name="participant_export"),
    path("register/<uuid:slug>/", views.participant_self_register, name="participant_self_register"),
    path("<int:pk>/", views.participant_detail, name="participant_detail"),
    path("<int:pk>/edit/", views.participant_edit, name="participant_edit"),
    path("<int:pk>/update/<str:token>/", views.participant_self_edit, name="participant_self_edit"),
    path("search/", views.participant_search, name="participant_search"),
    path("validate-bank/", views.validate_bank_ajax, name="validate_bank_ajax"),
]
