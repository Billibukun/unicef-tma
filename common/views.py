from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import CustomUser
from banks.models import Bank, BankAccount
from common.models import Channel
from devices.models import Device
from participants.models import Participant
from trainings.models import Training


@login_required
def dashboard(request):
    training_qs = Training.objects.all()
    context = {
        "training_count": training_qs.count(),
        "ongoing_count": training_qs.filter(status="ongoing").count(),
        "participant_count": Participant.objects.count(),
        "bank_account_count": BankAccount.objects.count(),
        "validated_bank_count": BankAccount.objects.filter(is_validated=True).count(),
        "device_count": Device.objects.count(),
        "assigned_device_count": Device.objects.filter(status="assigned").count(),
        "recent_trainings": training_qs[:10],
    }
    return render(request, "dashboard.html", context)


@login_required
def admin_tools(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    from django.contrib.auth.models import Group
    from trainings.models import Training
    from common.models import State

    users = CustomUser.objects.filter(is_active=True).select_related("channel", "state").order_by("first_name")
    groups = Group.objects.all()

    context = {
        "users": users,
        "groups": groups,
        "channels": Channel.objects.all(),
        "states": State.objects.all(),
        "bank_count": Bank.objects.filter(is_active=True).count(),
        "user_count": users.count(),
        "channel_count": Channel.objects.filter(is_active=True).count(),
        "training_count": Training.objects.count(),
        "participant_count": Participant.objects.count(),
    }
    return render(request, "admin_tools.html", context)


@login_required
def settings_view(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    from common.models import SystemSettings, TrainingRole
    sys_settings = SystemSettings.get()

    # Handle settings form save
    if request.method == "POST" and "save_settings" in request.POST:
        sys_settings.mileage_rate_per_km = request.POST.get("mileage_rate", 367)
        sys_settings.terminal_fee_per_leg = request.POST.get("terminal_fee_per_leg", 15000)
        sys_settings.save()
        messages.success(request, "Settings saved.")
        return redirect("settings")

    channels = Channel.objects.all()
    banks = Bank.objects.all().order_by("name")
    roles = TrainingRole.objects.select_related("channel").order_by("channel__name", "name")

    # Pagination for banks
    from django.core.paginator import Paginator
    per_page = request.GET.get("per_page", 15)
    bank_paginator = Paginator(banks, per_page)
    bank_page = bank_paginator.get_page(request.GET.get("page"))

    context = {
        "sys_settings": sys_settings,
        "channels": channels,
        "banks": bank_page,
        "roles": roles,
    }
    return render(request, "settings.html", context)


@login_required
def admin_add_user(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        channel_id = request.POST.get("channel") or None
        state_id = request.POST.get("state") or None
        group_id = request.POST.get("group") or None

        if username and password:
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                channel_id=channel_id,
                state_id=state_id,
            )
            if group_id:
                from django.contrib.auth.models import Group
                try:
                    group = Group.objects.get(pk=group_id)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass
            messages.success(request, f"User {username} created.")

    return redirect("admin_tools")
