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


def short_register(request, code):
    """Short URL redirect → full registration page."""
    from trainings.models import TrainingCategory
    category = get_object_or_404(TrainingCategory, short_code=code.upper())
    return redirect("participant_self_register", slug=category.slug)


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

            # Save proxy status on bank account
            is_proxy = "is_proxy" in request.POST
            proxy_name = request.POST.get("proxy_name", "").strip()
            try:
                ba = participant.bank_account
                if ba:
                    ba.is_proxy = is_proxy
                    ba.proxy_name = proxy_name
                    ba.save(update_fields=["is_proxy", "proxy_name"])
            except Exception:
                pass

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

            # Auto-assign cluster based on LGA
            if participant.lga:
                from trainings.models import TrainingCluster
                matching_cluster = TrainingCluster.objects.filter(
                    training=training, lgas=participant.lga
                ).first()
                if matching_cluster:
                    assignment_defaults["cluster"] = matching_cluster

            assignment, created = TrainingAssignment.objects.get_or_create(
                training=training,
                participant=participant,
                defaults=assignment_defaults,
            )
            if not created:
                # Update cluster if missing (e.g. registered before clusters were set up)
                updated_fields = []
                if not assignment.cluster and participant.lga:
                    from trainings.models import TrainingCluster
                    cluster = TrainingCluster.objects.filter(
                        training=training, lgas=participant.lga
                    ).first()
                    if cluster:
                        assignment.cluster = cluster
                        updated_fields.append("cluster")
                if not assignment.training_category:
                    assignment.training_category = category
                    updated_fields.append("training_category")
                if updated_fields:
                    assignment.save(update_fields=updated_fields)
                return render(request, "participants/participant_self_register.html", {
                    "form": form,
                    "training": training,
                    "category": category,
                    "duplicate_errors": [f"{participant.full_name} is already registered for this training."],
                })

            # Auto-create login for device managers
            login_credentials = None
            if category.is_device_manager and not participant.user:
                from accounts.models import CustomUser
                import secrets
                username = (participant.phone or participant.email or f"dm_{participant.pk}").replace("+", "").replace("@", "_")
                if CustomUser.objects.filter(username=username).exists():
                    username = f"{username}_{participant.pk}"
                temp_password = secrets.token_urlsafe(8)
                user = CustomUser.objects.create_user(
                    username=username,
                    password=temp_password,
                    first_name=participant.first_name,
                    last_name=participant.last_name,
                    email=participant.email,
                    state=training.state,
                    channel=participant.channel,
                )
                participant.user = user
                participant.save(update_fields=["user"])
                # Device managers are NOT training managers — they have separate access
                login_credentials = {"username": username, "password": temp_password}

                # Send login credentials via email
                if participant.email:
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings as app_settings
                        base_url = getattr(app_settings, "BASE_URL", "https://tma.worksiapps.com")
                        send_mail(
                            f"UNICEF TMA — Your Login Credentials",
                            f"Dear {participant.full_name},\n\n"
                            f"You have been registered as {category.name} for:\n"
                            f"{training.title} — {training.state}\n\n"
                            f"Your login credentials:\n"
                            f"  URL: {base_url}\n"
                            f"  Username: {username}\n"
                            f"  Password: {temp_password}\n\n"
                            f"Please log in and keep your credentials safe.\n\n"
                            f"—\n"
                            f"UNICEF Training Management Application\n"
                            f"Developed by Ibukunoluwa Omonijo",
                            None,
                            [participant.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

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
                "login_credentials": login_credentials,
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


def participant_self_edit(request, pk: int, token: str):
    """Public page for a participant to update their own profile (no login required).
    Token is a HMAC hash of participant pk to prevent unauthorized edits."""
    import hashlib
    import hmac
    from django.conf import settings as django_settings

    participant = get_object_or_404(Participant, pk=pk)

    # Verify token
    secret = getattr(django_settings, "SECRET_KEY", "fallback")
    expected = hmac.new(secret.encode(), str(pk).encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(token, expected):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Invalid link.")

    from common.models import LGA, State
    from .forms import ProfileEditForm

    if request.method == "POST":
        old_lga = participant.lga
        form = ProfileEditForm(request.POST, instance=participant)
        if form.is_valid():
            participant = form.save()
            changed_fields = form.changed_data

            # Send confirmation email
            if participant.email:
                from django.core.mail import send_mail
                changes_text = ", ".join(changed_fields)
                try:
                    send_mail(
                        "UNICEF TMA - Profile Updated",
                        f"Dear {participant.full_name},\n\n"
                        f"Your profile has been updated successfully.\n"
                        f"Updated fields: {changes_text}\n\n"
                        f"Current details:\n"
                        f"  Name: {participant.full_name}\n"
                        f"  Phone: {participant.phone}\n"
                        f"  Email: {participant.email}\n"
                        f"  State: {participant.state or '-'}\n"
                        f"  LGA: {participant.lga or '-'}\n"
                        f"  Ward: {participant.ward or '-'}\n\n"
                        f"If you did not make this change, please contact your training coordinator.\n\n"
                        f"---\nUNICEF Training Management Application",
                        None,
                        [participant.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            return render(request, "participants/participant_self_edit.html", {
                "participant": participant,
                "form": ProfileEditForm(instance=participant),
                "success": True,
                "changed_fields": changed_fields,
                "state_lgas": participant.state.lgas.all() if participant.state else LGA.objects.none(),
                "all_states": State.objects.all(),
            })
    else:
        form = ProfileEditForm(instance=participant)

    return render(request, "participants/participant_self_edit.html", {
        "participant": participant,
        "form": form,
        "state_lgas": participant.state.lgas.all() if participant.state else LGA.objects.none(),
        "all_states": State.objects.all(),
    })


def validate_bank_ajax(request):
    """Validate bank account number — returns HTML for HTMX or JSON for fetch."""
    from django.http import JsonResponse

    bank_id = request.GET.get("bank")
    account_number = request.GET.get("account_number", "").strip()
    wants_json = request.headers.get("Accept", "").startswith("application/json") or request.GET.get("format") == "json"

    if not bank_id or len(account_number) != 10:
        error = "Select a bank and enter a 10-digit account number" if bank_id or account_number else ""
        if wants_json:
            return JsonResponse({"valid": False, "error": error})
        return render(request, "participants/partials/bank_validation_result.html", {"error": error})

    from banks.models import Bank
    from banks.services import validate_bank_account

    try:
        bank = Bank.objects.get(pk=bank_id)
    except Bank.DoesNotExist:
        if wants_json:
            return JsonResponse({"valid": False, "error": "Invalid bank"})
        return render(request, "participants/partials/bank_validation_result.html", {"error": "Invalid bank"})

    result = validate_bank_account(account_number, bank)
    if wants_json:
        return JsonResponse({
            "valid": result.get("valid", False),
            "account_name": result.get("account_name", ""),
            "error": result.get("error", ""),
        })
    return render(request, "participants/partials/bank_validation_result.html", {"result": result})
