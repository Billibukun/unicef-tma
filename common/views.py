from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import CustomUser
from banks.models import Bank, BankAccount
from common.models import Channel
from devices.models import Device
from participants.models import Participant
from trainings.models import Training


@login_required
def dashboard(request):
    user = request.user

    # Filter trainings based on role
    training_qs = Training.objects.all()
    is_state_admin = user.groups.filter(name="State Admin").exists()
    is_training_manager = user.managed_trainings.exists()

    if is_state_admin and user.state:
        training_qs = training_qs.filter(state=user.state)
    elif is_training_manager and not user.is_superuser:
        if not user.groups.filter(name__in=["UNICEF Admin", "National Admin", "UNICEF HQ"]).exists():
            training_qs = user.managed_trainings.all()

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

    users = CustomUser.objects.filter(is_active=True).select_related("channel", "state").prefetch_related("groups", "managed_trainings").order_by("first_name")
    groups = Group.objects.all()

    # Identify device managers (users linked to participants)
    from participants.models import Participant
    device_manager_user_ids = set(
        Participant.objects.filter(user__isnull=False).values_list("user_id", flat=True)
    )

    context = {
        "users": users,
        "groups": groups,
        "device_manager_ids": device_manager_user_ids,
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
    is_unicef_admin = request.user.groups.filter(name="UNICEF Admin").exists()
    if not request.user.is_superuser and not is_unicef_admin:
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

    banks = Bank.objects.all().order_by("name")
    roles = TrainingRole.objects.select_related("channel").order_by("channel__name", "name")

    from django.core.paginator import Paginator
    per_page = request.GET.get("per_page", 15)
    bank_paginator = Paginator(banks, per_page)
    bank_page = bank_paginator.get_page(request.GET.get("page"))

    context = {
        "sys_settings": sys_settings,
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


@login_required
def admin_reset_password(request, user_id):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        user = get_object_or_404(CustomUser, pk=user_id)
        import secrets
        new_password = secrets.token_urlsafe(8)
        user.set_password(new_password)
        user.save()
        messages.success(request, f"Password reset for {user.username}. New password: {new_password}")

    return redirect("admin_tools")


@login_required
def upload_lgas(request):
    """Bulk upload LGAs from CSV. Format: state_name,lga_name (one per line)."""
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    if request.method == "POST" and request.FILES.get("file"):
        import csv, io
        from common.models import State, LGA
        f = request.FILES["file"]
        decoded = f.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(decoded))
        created = 0
        skipped = 0
        for row in reader:
            if len(row) < 2:
                continue
            state_name = row[0].strip()
            lga_name = row[1].strip()
            if not state_name or not lga_name:
                continue
            state = State.objects.filter(name__iexact=state_name).first()
            if not state:
                skipped += 1
                continue
            _, was_created = LGA.objects.get_or_create(state=state, name=lga_name)
            if was_created:
                created += 1
            else:
                skipped += 1
        messages.success(request, f"{created} LGAs created, {skipped} skipped.")

    return redirect("admin_tools")
