from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),
    path("forgot-password/", auth_views.PasswordResetView.as_view(
        template_name="accounts/forgot_password.html",
        email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/accounts/forgot-password/done/",
    ), name="password_reset"),
    path("forgot-password/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/forgot_password_done.html",
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/reset_confirm.html",
        success_url="/accounts/reset/done/",
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/reset_complete.html",
    ), name="password_reset_complete"),
]
