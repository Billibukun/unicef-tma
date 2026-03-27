from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from accounts.forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get("next", "dashboard")
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def change_password(request):
    from django.contrib.auth.decorators import login_required
    from django.contrib.auth import update_session_auth_hash
    from django.contrib import messages

    if not request.user.is_authenticated:
        return redirect("login")

    if request.method == "POST":
        current = request.POST.get("current_password", "")
        new1 = request.POST.get("new_password", "")
        new2 = request.POST.get("confirm_password", "")

        if not request.user.check_password(current):
            messages.error(request, "Current password is incorrect.")
        elif new1 != new2:
            messages.error(request, "New passwords don't match.")
        elif len(new1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            request.user.set_password(new1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect("dashboard")

    return render(request, "accounts/change_password.html")
