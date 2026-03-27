import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from banks.forms import BankAccountForm
from banks.models import BankAccount
from banks.services import validate_and_save


@login_required
def bank_account_list(request):
    qs = BankAccount.objects.select_related("participant", "bank")

    validated = request.GET.get("validated")
    if validated == "yes":
        qs = qs.filter(is_validated=True)
    elif validated == "no":
        qs = qs.filter(is_validated=False)

    search = request.GET.get("q")
    if search:
        qs = qs.filter(
            participant__first_name__icontains=search,
        ) | qs.filter(
            participant__last_name__icontains=search,
        ) | qs.filter(
            account_number__icontains=search,
        )

    return render(request, "banks/bank_account_list.html", {
        "accounts": qs,
        "current_validated": validated or "",
        "current_search": search or "",
    })


@login_required
def bank_account_create(request):
    from participants.models import Participant

    participant_id = request.GET.get("participant") or request.POST.get("participant")
    participant = None
    if participant_id:
        participant = Participant.objects.filter(pk=participant_id).first()

    if request.method == "POST":
        form = BankAccountForm(request.POST)
        if form.is_valid():
            ba = form.save(commit=False)
            ba.validated_by = request.user
            ba.save()
            # Auto-validate via Flutterwave
            result = validate_and_save(ba)
            if result["valid"]:
                messages.success(request, f"Bank account added and validated for {ba.participant}.")
            else:
                messages.warning(request, f"Bank account added for {ba.participant} but validation failed: {result.get('error', 'Unknown error')}. You can retry later.")
            if participant:
                return redirect("bank_account_list")
            return redirect("bank_account_list")
    else:
        initial = {}
        if participant_id:
            initial["participant"] = participant_id
        form = BankAccountForm(initial=initial)

    return render(request, "banks/bank_account_form.html", {
        "form": form,
        "title": "Add Bank Account",
        "participant": participant,
    })


@login_required
def validate_bank_account_view(request, pk: int):
    """HTMX endpoint: validate a single bank account, return partial."""
    ba = get_object_or_404(BankAccount, pk=pk)
    result = validate_and_save(ba)
    ba.refresh_from_db()

    return render(request, "banks/partials/validation_result.html", {
        "account": ba,
        "result": result,
    })


@login_required
def validate_all_view(request):
    """Validate all unvalidated bank accounts (batch)."""
    unvalidated = BankAccount.objects.filter(is_validated=False).select_related("bank")
    total = unvalidated.count()
    success_count = 0
    fail_count = 0

    for ba in unvalidated:
        result = validate_and_save(ba)
        if result["valid"]:
            success_count += 1
        else:
            fail_count += 1

    messages.success(request, f"Batch validation complete: {success_count}/{total} passed, {fail_count} failed.")
    return redirect("bank_account_list")


@login_required
def bank_account_export(request):
    """Export bank accounts as CSV with UNICEF codes."""
    qs = BankAccount.objects.select_related("participant", "bank").order_by(
        "participant__last_name", "participant__first_name"
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="bank_accounts_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Participant", "Bank Name", "UNICEF Bank Code", "CBN Code",
        "Account Number", "Account Name", "Validated", "Validation Method",
    ])

    for ba in qs:
        writer.writerow([
            ba.participant.full_name,
            ba.bank.name,
            ba.bank.unicef_code,
            ba.bank.cbn_code,
            ba.account_number,
            ba.account_name,
            "Yes" if ba.is_validated else "No",
            ba.get_validation_method_display() if ba.validation_method else "",
        ])

    return response
