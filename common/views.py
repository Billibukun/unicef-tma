from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
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

    # Device manager → DM dashboard
    is_device_manager = hasattr(user, "participant_profile") and user.participant_profile is not None
    if is_device_manager and not user.is_superuser and not user.groups.filter(name__in=["UNICEF Admin", "National Admin", "State Admin"]).exists():
        return redirect("dm:dashboard")

    from trainings.models import Event, EventChannel, TrainingAssignment

    user_groups = set(user.groups.values_list("name", flat=True))
    is_superadmin = user.is_superuser or "UNICEF Admin" in user_groups
    is_national = "National Admin" in user_groups
    is_state_admin = "State Admin" in user_groups
    is_training_manager = user.managed_trainings.exists()

    # --- Scope trainings ---
    training_qs = Training.objects.select_related("state", "channel", "event")
    if is_state_admin and not is_superadmin and not is_national:
        # State admins: managed trainings + fallback to state
        managed = user.managed_trainings.all()
        if managed.exists():
            training_qs = managed
        elif user.state:
            training_qs = training_qs.filter(state=user.state)
    elif is_training_manager and not is_superadmin and not is_national:
        training_qs = user.managed_trainings.all()

    # --- Events ---
    event_qs = Event.objects.prefetch_related("states", "trainings__state", "event_channels__channel")
    if is_state_admin and not is_superadmin and not is_national:
        if user.state:
            event_qs = event_qs.filter(states=user.state)
    elif is_training_manager and not is_superadmin and not is_national:
        event_qs = event_qs.filter(trainings__in=training_qs)

    events = event_qs.distinct()

    # --- Stats ---
    training_ids = list(training_qs.values_list("pk", flat=True))
    scoped_assignments = TrainingAssignment.objects.filter(training_id__in=training_ids)
    participant_count = scoped_assignments.values("participant_id").distinct().count()
    attended_count = scoped_assignments.filter(attended=True).count()
    total_assignments = scoped_assignments.count()
    att_rate = round(attended_count / total_assignments * 100) if total_assignments else 0

    p_ids = scoped_assignments.values_list("participant_id", flat=True)
    bank_total = BankAccount.objects.filter(participant_id__in=p_ids).count()
    bank_validated = BankAccount.objects.filter(participant_id__in=p_ids, is_validated=True).count()
    bank_missing = participant_count - bank_total

    if is_state_admin and user.state:
        device_total = Device.objects.filter(state=user.state).count()
        device_assigned = Device.objects.filter(state=user.state, status="assigned").count()
    else:
        device_total = Device.objects.count()
        device_assigned = Device.objects.filter(status="assigned").count()

    # --- Channel summary (superadmin/national) ---
    channel_stats = []
    if is_superadmin or is_national:
        for ch in Channel.objects.filter(is_active=True):
            ch_count = scoped_assignments.filter(
                models.Q(training_category__channel=ch) |
                models.Q(training_category__channel__isnull=True, training__channel=ch)
            ).count()
            if ch_count:
                channel_stats.append({"channel": ch, "count": ch_count})

    # --- Per-training stats for state admin cards ---
    training_cards = []
    for t in training_qs[:20]:
        t_assigns = t.assignments.count()
        t_attended = t.assignments.filter(attended=True).count()
        t_rate = round(t_attended / t_assigns * 100) if t_assigns else 0
        training_cards.append({
            "training": t,
            "participants": t_assigns,
            "attended": t_attended,
            "att_rate": t_rate,
        })

    # --- Ongoing events ---
    ongoing_events = events.filter(status="ongoing")

    context = {
        "user_groups": user_groups,
        "is_superadmin": is_superadmin,
        "is_national": is_national,
        "is_state_admin": is_state_admin,
        "training_count": len(training_ids),
        "ongoing_count": training_qs.filter(status="ongoing").count(),
        "participant_count": participant_count,
        "attended_count": attended_count,
        "att_rate": att_rate,
        "bank_total": bank_total,
        "bank_validated": bank_validated,
        "bank_missing": bank_missing,
        "device_total": device_total,
        "device_assigned": device_assigned,
        "events": events[:10],
        "ongoing_events": ongoing_events[:5],
        "training_cards": training_cards,
        "channel_stats": channel_stats,
        "user_state": user.state,
        "user_channel": user.channel,
    }

    # Role dispatch
    if is_superadmin:
        return render(request, "dashboards/superadmin.html", context)
    elif is_national:
        return render(request, "dashboards/national.html", context)
    elif is_state_admin:
        return render(request, "dashboards/state_admin.html", context)
    elif is_training_manager:
        return render(request, "dashboards/training_manager.html", context)
    return render(request, "dashboards/superadmin.html", context)


@login_required
def admin_tools(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    from django.contrib.auth.models import Group
    from trainings.models import Training
    from common.models import State

    users = CustomUser.objects.select_related("channel", "state").prefetch_related("groups", "managed_trainings").order_by("-is_active", "first_name")
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
def admin_users_page(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    from django.contrib.auth.models import Group
    from common.models import State
    from participants.models import Participant as P

    users = CustomUser.objects.select_related("channel", "state").prefetch_related("groups", "managed_trainings").order_by("-is_active", "first_name")
    dm_ids = set(P.objects.filter(user__isnull=False).values_list("user_id", flat=True))

    from django.core.paginator import Paginator
    paginator = Paginator(users, 25)
    users_page = paginator.get_page(request.GET.get("page"))

    return render(request, "admin_users.html", {
        "users": users_page,
        "groups": Group.objects.all(),
        "channels": Channel.objects.all(),
        "states": State.objects.all(),
        "device_manager_ids": dm_ids,
    })


@login_required
def admin_channels_page(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")
    return render(request, "admin_channels.html", {"channels": Channel.objects.all()})


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
def admin_edit_user(request, user_id):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    user = get_object_or_404(CustomUser, pk=user_id)

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.email = request.POST.get("email", "").strip()
        user.phone = request.POST.get("phone", "").strip()
        user.channel_id = request.POST.get("channel") or None
        user.state_id = request.POST.get("state") or None
        user.lga_id = request.POST.get("lga") or None
        user.save()

        # Update groups
        from django.contrib.auth.models import Group
        group_ids = request.POST.getlist("groups")
        user.groups.set(group_ids)

        messages.success(request, f"User {user.username} updated.")
        return redirect("admin_tools")

    from django.contrib.auth.models import Group
    from common.models import State, LGA

    return render(request, "edit_user.html", {
        "edit_user": user,
        "channels": Channel.objects.all(),
        "states": State.objects.all(),
        "lgas": LGA.objects.all(),
        "groups": Group.objects.all(),
        "user_groups": list(user.groups.values_list("pk", flat=True)),
    })


@login_required
def admin_toggle_user(request, user_id):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        user = get_object_or_404(CustomUser, pk=user_id)
        if user.pk != request.user.pk:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            status = "activated" if user.is_active else "deactivated"
            messages.success(request, f"User {user.username} {status}.")

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


def lgas_json(request):
    """Public JSON endpoint: return LGAs for a given state."""
    from django.http import JsonResponse
    from common.models import LGA
    state_id = request.GET.get("state")
    if not state_id:
        return JsonResponse([], safe=False)
    lgas = list(LGA.objects.filter(state_id=state_id).values("id", "name").order_by("name"))
    return JsonResponse(lgas, safe=False)


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
