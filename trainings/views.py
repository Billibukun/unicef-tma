from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from common.models import Channel

from .forms import TrainingForm
from .models import Training, TrainingCategory, TrainingCluster, TrainingLevel


def _settings_redirect(training):
    """Redirect back to training detail with settings modal open."""
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse("training_detail", args=[training.pk]) + "?settings=1")


@login_required
def training_list(request):
    qs = Training.objects.select_related("channel", "created_by")

    # Filters from GET params
    channel_id = request.GET.get("channel")
    status = request.GET.get("status")
    state = request.GET.get("state")

    if channel_id:
        qs = qs.filter(channel_id=channel_id)
    if status:
        qs = qs.filter(status=status)
    if state:
        qs = qs.filter(state_id=state)

    from django.core.paginator import Paginator
    from common.models import State
    per_page = request.GET.get("per_page", 15)
    paginator = Paginator(qs, per_page)
    page = request.GET.get("page")
    trainings_page = paginator.get_page(page)

    context = {
        "trainings": trainings_page,
        "states": State.objects.all(),
        "channels": Channel.objects.filter(is_active=True),
        "status_choices": Training.STATUS_CHOICES,
        "current_channel": channel_id or "",
        "current_status": status or "",
        "current_state": state or "",
    }
    return render(request, "trainings/training_list.html", context)


@login_required
def training_create(request):
    if request.method == "POST":
        form = TrainingForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.created_by = request.user
            training.save()
            messages.success(request, f'Training "{training.title}" created.')
            return redirect("training_detail", pk=training.pk)
    else:
        form = TrainingForm()

    return render(request, "trainings/training_form.html", {
        "form": form,
        "page_title": "Create Training",
    })


@login_required
def training_detail(request, pk: int):
    training = get_object_or_404(
        Training.objects.select_related("channel", "state", "created_by"),
        pk=pk,
    )
    levels = training.levels.all()
    categories = training.categories.prefetch_related("levels")
    clusters = training.clusters.prefetch_related("lgas")
    assignments = (
        training.assignments
        .select_related(
            "participant", "participant__channel", "participant__state",
            "role", "cluster", "training_category",
        )
        .order_by("training_category__name", "cluster__name", "participant__last_name")
    )

    # Filters
    cat_filter = request.GET.get("cat")
    cluster_filter = request.GET.get("cluster")
    role_filter = request.GET.get("role")
    if cat_filter:
        assignments = assignments.filter(training_category_id=cat_filter)
    if cluster_filter:
        assignments = assignments.filter(cluster_id=cluster_filter)
    if role_filter:
        assignments = assignments.filter(role_id=role_filter)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(assignments, 25)
    page = request.GET.get("page")
    assignments_page = paginator.get_page(page)

    # Financials summary
    financials = []
    for cat in categories:
        cat_assignments = cat.assignments.all()
        count = cat_assignments.count()
        cat_total = sum(a.total_payment for a in cat_assignments)
        financials.append({
            "category": cat,
            "count": count,
            "total": cat_total,
        })
    grand_total = sum(f["total"] for f in financials)

    from common.models import TrainingRole
    available_roles = TrainingRole.objects.filter(
        models.Q(channel=training.channel) | models.Q(channel__isnull=True)
    )

    return render(request, "trainings/training_detail.html", {
        "training": training,
        "levels": levels,
        "categories": categories,
        "clusters": clusters,
        "assignments": assignments_page,
        "total_assignments": paginator.count,
        "financials": financials,
        "grand_total": grand_total,
        "available_roles": available_roles,
        "state_lgas": training.state.lgas.all() if training.state else [],
        "cat_filter": cat_filter,
        "cluster_filter": cluster_filter,
        "role_filter": role_filter,
    })


@login_required
def training_edit(request, pk: int):
    training = get_object_or_404(Training, pk=pk)

    if request.method == "POST":
        form = TrainingForm(request.POST, instance=training)
        if form.is_valid():
            form.save()
            messages.success(request, f'Training "{training.title}" updated.')
            return redirect("training_detail", pk=training.pk)
    else:
        form = TrainingForm(instance=training)

    return render(request, "trainings/training_form.html", {
        "form": form,
        "training": training,
        "page_title": "Edit Training",
    })


@login_required
def training_delete(request, pk: int):
    training = get_object_or_404(Training, pk=pk)

    if request.method == "POST":
        title = training.title
        training.delete()
        messages.success(request, f'Training "{title}" deleted.')
        return redirect("training_list")

    return render(request, "trainings/training_confirm_delete.html", {
        "training": training,
    })


@login_required
def add_category(request, pk: int):
    """HTMX: add a category to a training."""
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        dsa_rate = request.POST.get("dsa_rate", 0)
        local_transport = request.POST.get("local_transport", 0)
        travel_mode = "enabled" if "travel_enabled" in request.POST else "none"
        expires = request.POST.get("registration_expires", "")

        level_ids = request.POST.getlist("levels")

        arrival_day = "arrival_day" in request.POST
        collect_nin = "collect_nin" in request.POST
        is_device_manager = "is_device_manager" in request.POST

        if name:
            from django.utils.dateparse import parse_datetime
            cat = TrainingCategory.objects.create(
                training=training,
                name=name,
                arrival_day=arrival_day,
                collect_nin=collect_nin,
                is_device_manager=is_device_manager,
                dsa_rate=dsa_rate or 0,
                local_transport=local_transport or 0,
                travel_mode=travel_mode,
                registration_expires=parse_datetime(expires) if expires else None,
            )
            if level_ids:
                cat.levels.set(level_ids)

    return _settings_redirect(training)


@login_required
def add_cluster(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        training_centre = request.POST.get("training_centre", "").strip()
        lga_ids = request.POST.getlist("lgas")
        if name:
            cluster, _ = TrainingCluster.objects.get_or_create(
                training=training, name=name,
                defaults={"training_centre": training_centre},
            )
            if lga_ids:
                cluster.lgas.set(lga_ids)
    return _settings_redirect(training)


@login_required
def toggle_category_registration(request, cat_id: int):
    cat = get_object_or_404(TrainingCategory.objects.select_related("training"), pk=cat_id)
    if request.method == "POST":
        cat.registration_open = not cat.registration_open
        if cat.registration_open:
            # Clear expiry when reopening so it doesn't block
            cat.registration_expires = None
        cat.save(update_fields=["registration_open", "registration_expires"])
    return _settings_redirect(cat.training)


@login_required
def edit_category(request, cat_id: int):
    cat = get_object_or_404(TrainingCategory.objects.select_related("training"), pk=cat_id)
    if request.method == "POST":
        cat.name = request.POST.get("name", cat.name).strip()
        cat.dsa_rate = request.POST.get("dsa_rate", cat.dsa_rate) or 0
        cat.local_transport = request.POST.get("local_transport", cat.local_transport) or 0
        cat.travel_mode = "enabled" if "travel_enabled" in request.POST else "none"
        cat.arrival_day = "arrival_day" in request.POST
        cat.collect_nin = "collect_nin" in request.POST
        cat.is_device_manager = "is_device_manager" in request.POST
        expires = request.POST.get("registration_expires", "")
        if expires:
            from django.utils.dateparse import parse_datetime
            cat.registration_expires = parse_datetime(expires)
        cat.save()
        level_ids = request.POST.getlist("levels")
        cat.levels.set(level_ids)
    # Regular redirect — modal will reopen via ?settings=1
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse("training_detail", args=[cat.training_id]) + "?settings=1")


@login_required
def delete_category(request, cat_id: int):
    cat = get_object_or_404(TrainingCategory.objects.select_related("training"), pk=cat_id)
    training = cat.training
    if request.method == "POST":
        cat.delete()
    return _settings_redirect(training)


@login_required
def edit_cluster(request, cluster_id: int):
    cluster = get_object_or_404(TrainingCluster.objects.select_related("training"), pk=cluster_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        training_centre = request.POST.get("training_centre", "").strip()
        if name:
            cluster.name = name
        cluster.training_centre = training_centre
        cluster.save()
        lga_ids = request.POST.getlist("lgas")
        cluster.lgas.set(lga_ids)
    return _settings_redirect(cluster.training)


@login_required
def assignment_detail(request, assignment_id: int):
    """Training-specific participant detail — shows only data for this training."""
    from trainings.models import TrainingAssignment
    assignment = get_object_or_404(
        TrainingAssignment.objects.select_related(
            "training", "training__state", "participant", "participant__channel",
            "participant__state", "participant__lga", "training_category", "cluster", "role",
        ),
        pk=assignment_id,
    )
    participant = assignment.participant
    training = assignment.training

    # Bank account
    bank_account = None
    try:
        bank_account = participant.bank_account
    except Exception:
        pass

    # Devices for this training only
    from devices.models import Device
    devices = Device.objects.filter(
        assigned_to=participant, training=training,
    ).select_related("state")

    return render(request, "trainings/assignment_detail.html", {
        "assignment": assignment,
        "participant": participant,
        "training": training,
        "bank_account": bank_account,
        "devices": devices,
    })


@login_required
def edit_assignment(request, assignment_id: int):
    """Edit training-specific data for a participant (role, category, cluster)."""
    from trainings.models import TrainingAssignment
    from common.models import TrainingRole
    assignment = get_object_or_404(
        TrainingAssignment.objects.select_related("training", "participant", "training_category", "cluster", "role"),
        pk=assignment_id,
    )
    training = assignment.training

    if request.method == "POST":
        assignment.role_id = request.POST.get("role") or None
        assignment.training_category_id = request.POST.get("category") or None
        assignment.cluster_id = request.POST.get("cluster") or None
        assignment.save()
        messages.success(request, f"Updated {assignment.participant.full_name}'s assignment.")
        return redirect("training_detail", pk=training.pk)

    categories = training.categories.all()
    clusters = training.clusters.all()
    roles = TrainingRole.objects.filter(
        models.Q(channel=training.channel) | models.Q(channel__isnull=True)
    )

    return render(request, "trainings/edit_assignment.html", {
        "assignment": assignment,
        "categories": categories,
        "clusters": clusters,
        "roles": roles,
    })


@login_required
def delete_cluster(request, cluster_id: int):
    cluster = get_object_or_404(TrainingCluster.objects.select_related("training"), pk=cluster_id)
    training = cluster.training
    if request.method == "POST":
        cluster.delete()
    return _settings_redirect(training)


@login_required
def update_cluster_lgas(request, cluster_id: int):
    cluster = get_object_or_404(TrainingCluster.objects.select_related("training"), pk=cluster_id)
    if request.method == "POST":
        lga_ids = request.POST.getlist("lgas")
        cluster.lgas.set(lga_ids)
    return _settings_redirect(cluster.training)


@login_required
def add_level(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        days = request.POST.get("days", 1) or 1
        if name:
            TrainingLevel.objects.get_or_create(
                training=training, name=name, defaults={"days": days}
            )
    return _settings_redirect(training)


@login_required
def delete_level(request, level_id: int):
    level = get_object_or_404(TrainingLevel.objects.select_related("training"), pk=level_id)
    training = level.training
    if request.method == "POST":
        level.delete()
    return _settings_redirect(training)


@login_required
def search_participants_for_training(request, pk: int):
    """HTMX: search participants to add to training."""
    from participants.models import Participant

    training = get_object_or_404(Training, pk=pk)
    q = request.GET.get("q", "").strip()
    results = []

    if len(q) >= 2:
        already_assigned = training.assignments.values_list("participant_id", flat=True)
        results = Participant.objects.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) |
            models.Q(email__icontains=q) | models.Q(phone__icontains=q)
        ).exclude(pk__in=already_assigned).select_related("channel", "state")[:10]

    return render(request, "trainings/partials/participant_search_results.html", {
        "results": results,
        "training": training,
        "q": q,
    })


@login_required
def assign_participant_to_training(request, pk: int):
    """Assign a participant to this training with role + category + cluster."""
    from participants.models import Participant
    from trainings.models import TrainingAssignment

    training = get_object_or_404(Training, pk=pk)

    if request.method == "POST":
        participant_id = request.POST.get("participant_id")
        role_id = request.POST.get("role") or None
        category_id = request.POST.get("category") or None
        cluster_id = request.POST.get("cluster") or None

        participant = get_object_or_404(Participant, pk=participant_id)

        from common.models import TrainingRole

        assignment, created = TrainingAssignment.objects.get_or_create(
            training=training,
            participant=participant,
            defaults={
                "role_id": role_id,
                "training_category_id": category_id,
                "cluster_id": cluster_id,
            },
        )
        if created:
            messages.success(request, f"{participant.full_name} added to training.")
        else:
            messages.info(request, f"{participant.full_name} is already assigned.")

    return redirect("training_detail", pk=pk)


@login_required
def remove_assignment(request, assignment_id: int):
    """Remove a participant from a training."""
    from trainings.models import TrainingAssignment

    assignment = get_object_or_404(TrainingAssignment, pk=assignment_id)
    training_pk = assignment.training_id
    name = assignment.participant.full_name

    if request.method == "POST":
        assignment.delete()
        messages.success(request, f"{name} removed from training.")

    return redirect("training_detail", pk=training_pk)


@login_required
def search_managers(request, pk: int):
    """HTMX: search users to add as training managers."""
    from accounts.models import CustomUser

    training = get_object_or_404(Training, pk=pk)
    q = request.GET.get("q", "").strip()
    results = []

    if len(q) >= 2:
        already = training.managers.values_list("pk", flat=True)
        results = CustomUser.objects.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) |
            models.Q(email__icontains=q) | models.Q(username__icontains=q)
        ).filter(is_active=True).exclude(pk__in=already)[:10]

    return render(request, "trainings/partials/manager_search_results.html", {
        "results": results, "training": training, "q": q,
    })


@login_required
def add_manager(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        from accounts.models import CustomUser
        user_id = request.POST.get("user_id")
        user = get_object_or_404(CustomUser, pk=user_id)
        training.managers.add(user)
    return _settings_redirect(training)


@login_required
def remove_manager(request, pk: int, user_id: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        from accounts.models import CustomUser
        user = get_object_or_404(CustomUser, pk=user_id)
        training.managers.remove(user)
    return _settings_redirect(training)


@login_required
def search_device_managers(request, pk: int):
    from accounts.models import CustomUser
    training = get_object_or_404(Training, pk=pk)
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 2:
        already = training.device_managers.values_list("pk", flat=True)
        results = CustomUser.objects.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) |
            models.Q(email__icontains=q) | models.Q(username__icontains=q)
        ).filter(is_active=True).exclude(pk__in=already)[:10]
    return render(request, "trainings/partials/device_manager_search_results.html", {
        "results": results, "training": training, "q": q,
    })


@login_required
def add_device_manager(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        from accounts.models import CustomUser
        user = get_object_or_404(CustomUser, pk=request.POST.get("user_id"))
        training.device_managers.add(user)
    return _settings_redirect(training)


@login_required
def remove_device_manager(request, pk: int, user_id: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        from accounts.models import CustomUser
        user = get_object_or_404(CustomUser, pk=user_id)
        training.device_managers.remove(user)
    return _settings_redirect(training)


@login_required
def toggle_devices(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        training.device_management = not training.device_management
        training.save(update_fields=["device_management"])
    return redirect("training_detail", pk=pk)


@login_required
def save_training_settings(request, pk: int):
    training = get_object_or_404(Training, pk=pk)
    if request.method == "POST":
        training.device_management = "device_management" in request.POST
        training.save(update_fields=["device_management"])
    return _settings_redirect(training)
