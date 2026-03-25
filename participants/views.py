import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from participants.forms import ParticipantForm, ParticipantImportForm, SelfRegistrationForm
from participants.models import Participant
from participants.services import export_participants_csv, import_participants_from_file


@login_required
def participant_list(request):
    qs = Participant.objects.select_related("channel")

    # Filters
    channel = request.GET.get("channel")
    state = request.GET.get("state")
    channel_role = request.GET.get("channel_role")
    search = request.GET.get("q")

    if channel:
        qs = qs.filter(channel_id=channel)
    if state:
        qs = qs.filter(state_id=state)
    if channel_role:
        qs = qs.filter(channel_role__icontains=channel_role)
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(email__icontains=search) | Q(phone__icontains=search)
        )

    from common.models import Channel, State
    channels = Channel.objects.filter(is_active=True)
    states = State.objects.all()

    from django.core.paginator import Paginator
    per_page = request.GET.get("per_page", 15)
    paginator = Paginator(qs, per_page)
    participants_page = paginator.get_page(request.GET.get("page"))

    return render(request, "participants/participant_list.html", {
        "participants": participants_page,
        "channels": channels,
        "states": states,
        "current_channel": channel,
        "current_state": state or "",
        "current_role": channel_role or "",
        "current_search": search or "",
    })


@login_required
def participant_create(request):
    if request.method == "POST":
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save()
            messages.success(request, f"Participant {participant.full_name} created.")
            return redirect("participant_detail", pk=participant.pk)
    else:
        form = ParticipantForm()

    from common.models import Channel
    channel_map = {str(c.pk): c.code for c in Channel.objects.filter(is_active=True)}

    return render(request, "participants/participant_form.html", {
        "form": form,
        "title": "Add Participant",
        "channel_map_json": json.dumps(channel_map),
    })


@login_required
def participant_detail(request, pk: int):
    participant = get_object_or_404(
        Participant.objects.select_related("channel"),
        pk=pk,
    )

    bank_account = None
    try:
        bank_account = participant.bank_account
    except Exception:
        pass

    assignments = participant.training_assignments.select_related(
        "training", "training_category", "cluster",
    ).order_by("-training__start_date")

    from devices.models import Device
    devices = Device.objects.filter(assigned_to=participant).select_related("training", "state")

    return render(request, "participants/participant_detail.html", {
        "participant": participant,
        "devices": devices,
        "bank_account": bank_account,
        "assignments": assignments,
    })


@login_required
def participant_edit(request, pk: int):
    participant = get_object_or_404(Participant, pk=pk)

    if request.method == "POST":
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            form.save()
            messages.success(request, "Participant updated.")
            return redirect("participant_detail", pk=participant.pk)
    else:
        form = ParticipantForm(instance=participant)

    from common.models import Channel
    channel_map = {str(c.pk): c.code for c in Channel.objects.filter(is_active=True)}

    return render(request, "participants/participant_form.html", {
        "form": form,
        "title": f"Edit {participant.full_name}",
        "participant": participant,
        "channel_map_json": json.dumps(channel_map),
    })


@login_required
def participant_import(request):
    if request.method == "POST":
        form = ParticipantImportForm(request.POST, request.FILES)
        if form.is_valid():
            result = import_participants_from_file(request.FILES["file"])
            if result["created"]:
                messages.success(request, f"{result['created']} participant(s) imported.")
            if result["skipped"]:
                messages.info(request, f"{result['skipped']} duplicate(s) skipped.")
            if result["errors"]:
                messages.warning(request, f"{result['errors']} row(s) had errors.")
            return render(request, "participants/participant_import.html", {
                "form": ParticipantImportForm(),
                "result": result,
            })
    else:
        form = ParticipantImportForm()

    return render(request, "participants/participant_import.html", {"form": form})


@login_required
def participant_export(request):
    qs = Participant.objects.select_related("channel")

    channel = request.GET.get("channel")
    state = request.GET.get("state")
    if channel:
        qs = qs.filter(channel_id=channel)
    if state:
        qs = qs.filter(state__icontains=state)

    return export_participants_csv(qs)


def participant_self_register(request, slug):
    """Public self-registration via training category link (no login required)."""
    from django.http import HttpResponse
    from trainings.models import TrainingAssignment, TrainingCategory

    category = get_object_or_404(TrainingCategory, slug=slug)
    training = category.training

    # Check if registration is active
    if not category.is_registration_active:
        return render(request, "participants/participant_self_register.html", {
            "closed": True,
            "training": training,
            "category": category,
        })

    if request.method == "POST":
        form = SelfRegistrationForm(request.POST)
        if form.is_valid():
            # Check for duplicates in this training
            phone = form.cleaned_data.get("phone", "").strip()
            email = form.cleaned_data.get("email", "").strip()
            account_number = form.cleaned_data.get("account_number", "").strip()

            from django.db.models import Q
            existing_participants = training.assignments.values_list("participant_id", flat=True)
            duplicate_checks = []

            if phone:
                dup = Participant.objects.filter(phone=phone, pk__in=existing_participants).first()
                if dup:
                    duplicate_checks.append(f"Phone number {phone} is already registered for this training ({dup.full_name})")

            if email:
                dup = Participant.objects.filter(email__iexact=email, pk__in=existing_participants).first()
                if dup:
                    duplicate_checks.append(f"Email {email} is already registered for this training ({dup.full_name})")

            if account_number:
                from banks.models import BankAccount
                dup_bank = BankAccount.objects.filter(
                    account_number=account_number,
                    participant_id__in=existing_participants,
                ).select_related("participant").first()
                if dup_bank:
                    duplicate_checks.append(f"Account {account_number} is already registered for this training ({dup_bank.participant.full_name})")

            if duplicate_checks:
                from common.models import State
                return render(request, "participants/participant_self_register.html", {
                    "form": form,
                    "training": training,
                    "category": category,
                    "duplicate_errors": duplicate_checks,
                    "state_lgas": training.state.lgas.all() if training.state else [],
                    "all_states": State.objects.all(),
                })

            # Check if participant already exists (reuse record)
            participant = None
            if phone:
                participant = Participant.objects.filter(phone=phone).first()
            if not participant and email:
                participant = Participant.objects.filter(email__iexact=email).first()

            if participant:
                # Update existing record with new data
                for field in ["first_name", "last_name", "channel", "channel_role",
                              "health_organization", "origin", "state", "lga"]:
                    val = form.cleaned_data.get(field)
                    if val:
                        setattr(participant, field, val)
                participant.save()
            else:
                participant = form.save()

            # Save NIN if provided
            nin = request.POST.get("nin", "").strip()
            if nin:
                participant.nin = nin
                participant.save(update_fields=["nin"])

            # Link to this training + category
            assignment_defaults = {"training_category": category}

            # Save travel data if category has travel enabled
            if category.travel_mode != "none":
                assignment_defaults["outbound_mode"] = request.POST.get("outbound_mode", "none")
                assignment_defaults["outbound_from_id"] = request.POST.get("outbound_from") or None
                assignment_defaults["outbound_to_id"] = training.state_id
                assignment_defaults["return_mode"] = request.POST.get("return_mode", "none")
                assignment_defaults["return_from_id"] = training.state_id
                assignment_defaults["return_to_id"] = request.POST.get("return_to") or None

                # Auto-calculate mileage for road legs
                from trainings.models import TrainingAssignment as TA
                temp = TA(**assignment_defaults, training=training, participant=participant)
                temp.calculate_mileage()
                assignment_defaults["outbound_mileage"] = temp.outbound_mileage
                assignment_defaults["return_mileage"] = temp.return_mileage

            assignment, created = TrainingAssignment.objects.get_or_create(
                training=training,
                participant=participant,
                defaults=assignment_defaults,
            )
            if not created:
                return render(request, "participants/participant_self_register.html", {
                    "form": form,
                    "training": training,
                    "category": category,
                    "duplicate_errors": [f"{participant.full_name} is already registered for this training."],
                })

            # Validate bank account immediately
            bank_result = None
            try:
                ba = participant.bank_account
                if ba and not ba.is_validated:
                    from banks.services import validate_and_save
                    result = validate_and_save(ba)
                    bank_result = {
                        "success": result["valid"],
                        "account_name": result.get("account_name", ""),
                        "error": result.get("error", ""),
                    }
            except Exception:
                pass

            return render(request, "participants/participant_self_register.html", {
                "success": True,
                "participant": participant,
                "training": training,
                "category": category,
                "bank_validation_result": bank_result,
            })
    else:
        form = SelfRegistrationForm()

    from common.models import State
    state_lgas = training.state.lgas.all() if training.state else []
    all_states = State.objects.all()

    return render(request, "participants/participant_self_register.html", {
        "form": form,
        "training": training,
        "category": category,
        "state_lgas": state_lgas,
        "all_states": all_states,
    })


@login_required
def participant_search(request):
    """Global participant search — HTMX endpoint."""
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 2:
        from django.db.models import Q
        results = Participant.objects.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(email__icontains=q) | Q(phone__icontains=q)
        ).select_related("channel", "state")[:20]

    return render(request, "participants/partials/search_results.html", {"results": results, "q": q})


def validate_bank_ajax(request):
    """HTMX: validate bank account number and return account name."""
    bank_id = request.GET.get("bank")
    account_number = request.GET.get("account_number", "").strip()

    if not bank_id or len(account_number) != 10:
        return render(request, "participants/partials/bank_validation_result.html", {
            "error": "Select a bank and enter a 10-digit account number" if bank_id or account_number else "",
        })

    from banks.models import Bank
    from banks.services import validate_bank_account

    try:
        bank = Bank.objects.get(pk=bank_id)
    except Bank.DoesNotExist:
        return render(request, "participants/partials/bank_validation_result.html", {"error": "Invalid bank"})

    result = validate_bank_account(account_number, bank)
    return render(request, "participants/partials/bank_validation_result.html", {
        "result": result,
    })
