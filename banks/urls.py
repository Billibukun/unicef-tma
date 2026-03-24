from django.urls import path

from banks import views

urlpatterns = [
    path("", views.bank_account_list, name="bank_account_list"),
    path("create/", views.bank_account_create, name="bank_account_create"),
    path("<int:pk>/validate/", views.validate_bank_account_view, name="bank_validate"),
    path("validate-all/", views.validate_all_view, name="bank_validate_all"),
    path("export/", views.bank_account_export, name="bank_account_export"),
]
