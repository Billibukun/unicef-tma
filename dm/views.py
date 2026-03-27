from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from banks.models import BankAccount
from devices.models import Device
from participants.models import Participant
from trainings.models import TrainingAssignment

from .decorators import dm_required


def _dm_ctx(request):
    """Common context for all DM templates."""
    return {
        "dm_participant": request.dm_participant,
        "dm_training": request.dm_training,
        "dm_lga": request.dm_lga,
        "dm_cluster": request.dm_cluster,
    }


@dm_required
def dm_dashboard(request):
    training = request.dm_training
    lga = request.dm_lga

    # Participant stats for this LGA in this training
    lga_assignments = training.assignments.filter(
        participant__lga=lga,
    ).select_related("participant")
    total = lga_assignments.count()
    attended = lga_assignments.filter(attended=True).count()
    absent = lga_assignments.filter(attended=False).count()
    unmarked = total - attended - absent

    # Bank stats
    lga_participant_ids = lga_assignments.values_list("participant_id", flat=True)
    bank_has = BankAccount.objects.filter(participant_id__in=lga_participant_ids).count()
    bank_validated = BankAccount.objects.filter(
        participant_id__in=lga_participant_ids, is_validated=True
    ).count()
    bank_missing = total - bank_has

    # Device stats for this LGA
    lga_devices = Device.objects.filter(lga=lga)
    device_total = lga_devices.count()
    device_assigned = lga_devices.filter(status="assigned").count()
    device_available = device_total - device_assigned

    # Phone issues — missing or invalid
    import re
    phone_issues = 0
    for a in lga_assignments:
        p = a.participant
        if not p.phone or not re.match(r"^0[789]\d{9}$", p.phone):
            phone_issues += 1

    # Attendance rate
    att_rate = round(attended / total * 100) if total > 0 else 0

    # Cluster summary
    cluster_stats = []
    if request.dm_cluster:
        for cl_lga in request.dm_cluster.lgas.all().order_by("name"):
            cl_assigns = training.assignments.filter(participant__lga=cl_lga)
            cl_devices = Device.objects.filter(lga=cl_lga)
            cl_attended = cl_assigns.filter(attended=True).count()
            cl_total = cl_assigns.count()
            cluster_stats.append({
                "lga": cl_lga,
                "is_mine": cl_lga == lga,
                "participants": cl_total,
                "attended": cl_attended,
                "devices": cl_devices.count(),
            })

    ctx = _dm_ctx(request)
    ctx.update({
        "total": total,
        "attended": attended,
        "absent": absent,
        "unmarked": unmarked,
        "att_rate": att_rate,
        "bank_has": bank_has,
        "bank_validated": bank_validated,
        "bank_missing": bank_missing,
        "device_total": device_total,
        "device_assigned": device_assigned,
        "device_available": device_available,
        "phone_issues": phone_issues,
        "cluster_stats": cluster_stats,
    })
    return render(request, "dm/dashboard.html", ctx)


@dm_required
def dm_participants(request):
    training = request.dm_training
    lga = request.dm_lga

    qs = training.assignments.filter(
        participant__lga=lga,
    ).select_related("participant", "participant__channel", "training_category")

    # Filters
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status")
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(participant__first_name__icontains=q) |
            Q(participant__last_name__icontains=q) |
            Q(participant__phone__icontains=q)
        )
    if status == "attended":
        qs = qs.filter(attended=True)
    elif status == "absent":
        qs = qs.filter(attended=False)
    elif status == "unmarked":
        qs = qs.filter(attended__isnull=True)
    elif status == "no_bank":
        has_bank_ids = BankAccount.objects.values_list("participant_id", flat=True)
        qs = qs.exclude(participant_id__in=has_bank_ids)
    elif status == "bad_phone":
        import re
        valid_ids = [
            a.participant_id for a in qs
            if a.participant.phone and re.match(r"^0[789]\d{9}$", a.participant.phone)
        ]
        qs = qs.exclude(participant_id__in=valid_ids)

    paginator = Paginator(qs.order_by("participant__last_name"), 25)
    page = paginator.get_page(request.GET.get("page"))

    ctx = _dm_ctx(request)
    ctx.update({
        "assignments": page,
        "current_q": q,
        "current_status": status or "",
    })
    return render(request, "dm/participants.html", ctx)


@dm_required
def dm_participant_profile(request, assignment_id: int):
    training = request.dm_training
    lga = request.dm_lga

    assignment = get_object_or_404(
        TrainingAssignment.objects.select_related(
            "participant", "participant__channel", "participant__state",
            "participant__lga", "training_category", "cluster",
        ),
        pk=assignment_id,
        training=training,
        participant__lga=lga,
    )
    participant = assignment.participant

    # Bank account
    bank_account = None
    try:
        bank_account = participant.bank_account
    except BankAccount.DoesNotExist:
        pass

    # Assigned device
    device = Device.objects.filter(assigned_to=participant, lga=lga).first()

    ctx = _dm_ctx(request)
    ctx.update({
        "assignment": assignment,
        "participant": participant,
        "bank_account": bank_account,
        "device": device,
    })
    return render(request, "dm/participant_profile.html", ctx)


@dm_required
def dm_toggle_attendance(request, assignment_id: int):
    training = request.dm_training
    lga = request.dm_lga

    assignment = get_object_or_404(
        TrainingAssignment,
        pk=assignment_id,
        training=training,
        participant__lga=lga,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "present":
            assignment.attended = True
        elif action == "absent":
            assignment.attended = False
        else:
            assignment.attended = None
        assignment.attended_marked_by = request.user
        assignment.save(update_fields=["attended", "attended_marked_by"])

    return render(request, "dm/partials/attendance_btn.html", {"a": assignment})


@dm_required
def dm_send_edit_link(request, assignment_id: int):
    from django.conf import settings as s
    from django.core.mail import send_mail

    training = request.dm_training
    lga = request.dm_lga

    assignment = get_object_or_404(
        TrainingAssignment.objects.select_related("participant"),
        pk=assignment_id,
        training=training,
        participant__lga=lga,
    )
    p = assignment.participant

    if request.method == "POST" and p.email:
        base = getattr(s, "BASE_URL", "https://tma.worksiapps.com")
        link = f"{base}{p.edit_url}"
        try:
            send_mail(
                "UNICEF TMA - Update Your Profile",
                f"Dear {p.full_name},\n\n"
                f"Please update your profile using this link:\n{link}\n\n"
                f"---\nUNICEF Training Management Application",
                None, [p.email], fail_silently=True,
            )
            messages.success(request, f"Edit link sent to {p.email}")
        except Exception:
            messages.error(request, "Failed to send email.")
    elif not p.email:
        messages.warning(request, "This participant has no email address.")

    return redirect("dm:participant_profile", assignment_id=assignment_id)


@dm_required
def dm_devices(request):
    lga = request.dm_lga
    qs = Device.objects.filter(lga=lga).select_related("assigned_to")

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(serial_number__icontains=q) | Q(imei_1__icontains=q)
        )

    paginator = Paginator(qs.order_by("-created_at"), 25)
    page = paginator.get_page(request.GET.get("page"))

    ctx = _dm_ctx(request)
    ctx.update({
        "devices": page,
        "current_status": status or "",
        "current_q": q,
    })
    return render(request, "dm/devices.html", ctx)


@dm_required
def dm_scan(request):
    ctx = _dm_ctx(request)
    return render(request, "dm/scan.html", ctx)


@dm_required
def dm_device_detail(request, pk: int):
    lga = request.dm_lga
    device = get_object_or_404(
        Device.objects.select_related("assigned_to", "training", "lga"),
        pk=pk, lga=lga,
    )

    ctx = _dm_ctx(request)
    ctx.update({"device": device})
    return render(request, "dm/device_detail.html", ctx)


@dm_required
def dm_device_assign(request, pk: int):
    lga = request.dm_lga
    device = get_object_or_404(Device, pk=pk, lga=lga)

    if request.method == "POST":
        participant_id = request.POST.get("participant")
        if participant_id:
            participant = get_object_or_404(Participant, pk=participant_id, lga=lga)
            device.assigned_to = participant
            device.assigned_by = request.user
            device.status = "assigned"
        else:
            device.assigned_to = None
            device.assigned_by = None
            device.status = "available"
        device.save()
        messages.success(request, f"Device {device.serial_number} updated.")

    return redirect("dm:device_detail", pk=pk)
