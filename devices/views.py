import csv
import io
import json

from django.db import models
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from participants.models import Participant
from trainings.models import Training

from .forms import DeviceBulkUploadForm, DeviceForm
from .models import Device, DeviceLog


@login_required
def device_list(request):
    qs = Device.objects.select_related("assigned_to", "training")

    # Filters
    status = request.GET.get("status")
    state = request.GET.get("state")
    device_type = request.GET.get("device_type")
    q = request.GET.get("q", "").strip()

    if status:
        qs = qs.filter(status=status)
    if state:
        qs = qs.filter(state_id=state)
    if device_type:
        qs = qs.filter(device_type=device_type)
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(serial_number__icontains=q) | Q(imei_1__icontains=q) |
            Q(imei_2__icontains=q) | Q(brand__icontains=q)
        )

    from django.core.paginator import Paginator
    per_page = request.GET.get("per_page", 15)
    paginator = Paginator(qs, per_page)
    devices_page = paginator.get_page(request.GET.get("page"))

    from common.models import State
    context = {
        "devices": devices_page,
        "states": State.objects.all(),
        "status_choices": Device.STATUS_CHOICES,
        "type_choices": Device.DEVICE_TYPE_CHOICES,
        "current_status": status or "",
        "current_state": state or "",
        "current_type": device_type or "",
        "current_q": q,
    }
    return render(request, "devices/device_list.html", context)


@login_required
def device_create(request):
    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.uploaded_by = request.user
            device.save()
            messages.success(request, f"Device {device.serial_number} created.")
            return redirect("device_detail", pk=device.pk)
    else:
        form = DeviceForm()
    return render(request, "devices/device_form.html", {"form": form, "title": "Add Device"})


@login_required
def device_detail(request, pk: int):
    device = get_object_or_404(
        Device.objects.select_related("assigned_to", "training", "uploaded_by"),
        pk=pk,
    )
    participants = Participant.objects.all()
    trainings = Training.objects.all()
    return render(request, "devices/device_detail.html", {
        "device": device,
        "participants": participants,
        "trainings": trainings,
    })


@login_required
def device_edit(request, pk: int):
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            messages.success(request, f"Device {device.serial_number} updated.")
            return redirect("device_detail", pk=device.pk)
    else:
        form = DeviceForm(instance=device)
    return render(request, "devices/device_form.html", {
        "form": form,
        "title": "Edit Device",
        "device": device,
    })


@login_required
def device_scan(request):
    """Barcode scanner page."""
    from common.models import State, LGA

    # If scanning for a specific training, lock the state
    training_id = request.GET.get("training")
    training = None
    lgas = LGA.objects.none()
    if training_id:
        training = Training.objects.filter(pk=training_id).select_related("state").first()

    if training and training.state:
        lgas = LGA.objects.filter(state=training.state)
    elif request.user.state:
        lgas = LGA.objects.filter(state=request.user.state)

    states = State.objects.all()
    return render(request, "devices/device_scan.html", {
        "training": training,
        "states": states,
        "lgas": lgas,
    })


@login_required
def device_save_scanned(request):
    """HTMX endpoint: receives labeled scanned values and creates a Device."""
    if request.method != "POST":
        return HttpResponse(status=405)

    serial_number = request.POST.get("serial_number", "").strip()
    imei_1 = request.POST.get("imei_1", "").strip()
    imei_2 = request.POST.get("imei_2", "").strip()
    device_type = request.POST.get("device_type", "tablet").strip()
    brand = request.POST.get("brand", "").strip()
    model_name = request.POST.get("model_name", "").strip()
    state_id = request.POST.get("state", "").strip() or None
    lga_id = request.POST.get("lga", "").strip() or None
    training_id = request.POST.get("training", "").strip() or None

    errors = []
    if not serial_number:
        errors.append("Serial number is required.")
    if serial_number and Device.objects.filter(serial_number=serial_number).exists():
        errors.append(f"Device with serial number '{serial_number}' already exists.")
    if imei_1 and Device.objects.filter(models.Q(imei_1=imei_1) | models.Q(imei_2=imei_1)).exists():
        errors.append(f"IMEI {imei_1} already exists on another device.")
    if imei_2 and Device.objects.filter(models.Q(imei_1=imei_2) | models.Q(imei_2=imei_2)).exists():
        errors.append(f"IMEI {imei_2} already exists on another device.")

    if errors:
        return render(request, "devices/partials/device_saved.html", {
            "success": False,
            "errors": errors,
        })

    condition = request.POST.get("condition", "good")
    status = request.POST.get("status", "available")
    accessories = request.POST.get("accessories_complete", "1") == "1"
    comment = request.POST.get("comment", "").strip()

    device = Device.objects.create(
        serial_number=serial_number,
        imei_1=imei_1,
        imei_2=imei_2,
        device_type=device_type,
        brand=brand,
        model_name=model_name,
        state_id=state_id,
        lga_id=lga_id,
        training_id=training_id,
        condition=condition,
        status=status,
        accessories_complete=accessories,
        comment=comment,
        uploaded_by=request.user,
    )

    return render(request, "devices/partials/device_saved.html", {
        "success": True,
        "device": device,
    })


@login_required
def device_assign(request, pk: int):
    """Assign a device to a participant (and optionally a training)."""
    device = get_object_or_404(Device, pk=pk)

    if request.method == "POST":
        participant_id = request.POST.get("participant")
        training_id = request.POST.get("training")

        if participant_id:
            participant = get_object_or_404(Participant, pk=participant_id)
            device.assigned_to = participant
            device.status = "assigned"
        else:
            device.assigned_to = None
            device.status = "available"

        if training_id:
            training = get_object_or_404(Training, pk=training_id)
            device.training = training
        else:
            device.training = None

        device.save()
        action = "assigned" if device.assigned_to else "unassigned"
        messages.success(request, f"Device {device.serial_number} {action}.")

    return redirect("device_detail", pk=device.pk)


@login_required
def device_bulk_upload(request):
    """Upload devices via CSV."""
    if request.method == "POST":
        form = DeviceBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            decoded = csv_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            skipped = 0
            for row in reader:
                sn = row.get("serial_number", "").strip()
                if not sn or Device.objects.filter(serial_number=sn).exists():
                    skipped += 1
                    continue
                Device.objects.create(
                    serial_number=sn,
                    imei_1=row.get("imei_1", "").strip(),
                    imei_2=row.get("imei_2", "").strip(),
                    device_type=row.get("device_type", "tablet").strip(),
                    brand=row.get("brand", "").strip(),
                    model_name=row.get("model_name", "").strip(),
                    state=row.get("state", "").strip(),
                    lga=row.get("lga", "").strip(),
                    uploaded_by=request.user,
                )
                created += 1

            messages.success(request, f"Uploaded {created} devices. Skipped {skipped}.")
            return redirect("device_list")
    else:
        form = DeviceBulkUploadForm()

    return render(request, "devices/device_form.html", {
        "form": form,
        "title": "Bulk Upload Devices",
        "is_bulk": True,
    })


@login_required
def device_update_status(request, pk: int):
    """Update device status/condition with a log entry."""
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status", device.status)
        new_condition = request.POST.get("condition", device.condition)
        note = request.POST.get("note", "").strip()

        device.status = new_status
        device.condition = new_condition
        device.save(update_fields=["status", "condition", "updated_at"])

        DeviceLog.objects.create(
            device=device,
            status=new_status,
            condition=new_condition,
            note=note,
            created_by=request.user,
        )
        messages.success(request, f"Device {device.serial_number} updated.")

    return redirect("device_detail", pk=pk)


@login_required
def device_search(request):
    """Global device search — HTMX endpoint."""
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 2:
        from django.db.models import Q
        results = Device.objects.filter(
            Q(serial_number__icontains=q) | Q(imei_1__icontains=q) |
            Q(imei_2__icontains=q) | Q(brand__icontains=q)
        ).select_related("assigned_to", "training", "state")[:20]

    return render(request, "devices/partials/search_results.html", {"results": results, "q": q})
