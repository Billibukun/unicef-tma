import csv
import io
import logging

from django.db import transaction
from django.http import HttpResponse

from banks.models import Bank, BankAccount
from common.models import Channel
from participants.models import Participant

logger = logging.getLogger(__name__)

# Column name mappings (lowercase) -> model field
FIELD_MAP = {
    "first_name": "first_name",
    "first name": "first_name",
    "firstname": "first_name",
    "last_name": "last_name",
    "last name": "last_name",
    "lastname": "last_name",
    "surname": "last_name",
    "email": "email",
    "phone": "phone",
    "phone_number": "phone",
    "phone number": "phone",
    "channel": "channel",
    "channel_role": "channel_role",
    "channel role": "channel_role",
    "role": "channel_role",
    "health_organization": "health_organization",
    "health organization": "health_organization",
    "organization": "health_organization",
    "origin": "origin",
    "state": "state",
    "lga": "lga",
    # Bank columns
    "bank": "bank_name",
    "bank_name": "bank_name",
    "bank name": "bank_name",
    "account_number": "account_number",
    "account number": "account_number",
    "account_no": "account_number",
}


def _read_file_rows(file) -> list[dict]:
    """Read rows from CSV or Excel file into list of dicts."""
    filename = file.name.lower()

    if filename.endswith((".xlsx", ".xls")):
        try:
            import openpyxl
        except ImportError:
            raise ValueError("openpyxl is required for Excel files. Install with: pip install openpyxl")

        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h).strip().lower() if h else "" for h in next(rows_iter)]
        rows = []
        for row in rows_iter:
            row_dict = {}
            for header, value in zip(headers, row):
                if header and value is not None:
                    row_dict[header] = str(value).strip()
            if any(row_dict.values()):
                rows.append(row_dict)
        wb.close()
        return rows

    # CSV
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        if any(cleaned.values()):
            rows.append(cleaned)
    return rows


def import_participants_from_file(file) -> dict:
    """Import participants from CSV/Excel file.

    Returns dict with created, skipped, errors counts and error_rows list.
    """
    rows = _read_file_rows(file)
    if not rows:
        return {"created": 0, "skipped": 0, "errors": 0, "error_rows": []}

    # Pre-fetch lookups
    channels = {c.code.lower(): c for c in Channel.objects.filter(is_active=True)}
    channels_by_name = {c.name.lower(): c for c in Channel.objects.filter(is_active=True)}
    banks_by_name = {b.name.lower(): b for b in Bank.objects.filter(is_active=True)}
    banks_by_short = {b.short_name.lower(): b for b in Bank.objects.filter(is_active=True) if b.short_name}

    created = 0
    skipped = 0
    errors = 0
    error_rows = []

    for i, row in enumerate(rows, start=2):  # start=2 because row 1 is header
        mapped = {}
        for col_name, value in row.items():
            field = FIELD_MAP.get(col_name)
            if field:
                mapped[field] = value

        first_name = mapped.get("first_name", "").strip()
        last_name = mapped.get("last_name", "").strip()
        if not first_name or not last_name:
            error_rows.append({"row": i, "error": "Missing first_name or last_name"})
            errors += 1
            continue

        # Resolve channel
        channel_val = mapped.get("channel", "").strip().lower()
        channel = channels.get(channel_val) or channels_by_name.get(channel_val)
        if not channel:
            error_rows.append({"row": i, "error": f"Unknown channel: {mapped.get('channel', '')}"})
            errors += 1
            continue

        try:
            with transaction.atomic():
                participant, was_created = Participant.objects.get_or_create(
                    first_name=first_name,
                    last_name=last_name,
                    channel=channel,
                    defaults={
                        "email": mapped.get("email", ""),
                        "phone": mapped.get("phone", ""),
                        "channel_role": mapped.get("channel_role", ""),
                        "health_organization": mapped.get("health_organization", ""),
                        "origin": mapped.get("origin", ""),
                        "state": mapped.get("state", ""),
                        "lga": mapped.get("lga", ""),
                    },
                )

                if not was_created:
                    skipped += 1
                    continue

                # Create bank account if columns present
                bank_name_val = mapped.get("bank_name", "").strip().lower()
                account_number = mapped.get("account_number", "").strip()

                if bank_name_val and account_number:
                    bank = banks_by_name.get(bank_name_val) or banks_by_short.get(bank_name_val)
                    if bank:
                        BankAccount.objects.create(
                            participant=participant,
                            bank=bank,
                            account_number=account_number,
                        )

                created += 1
        except Exception as e:
            logger.error("Row %d import error: %s", i, e)
            error_rows.append({"row": i, "error": str(e)})
            errors += 1

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "error_rows": error_rows,
    }


def export_participants_csv(queryset) -> HttpResponse:
    """Export participants as CSV with UNICEF bank codes."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="participants_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "First Name", "Last Name", "Email", "Phone",
        "Channel", "Channel Role", "Health Organization",
        "Origin", "State", "LGA",
        "Bank Name", "UNICEF Bank Code", "Account Number",
        "Account Name", "Validated",
    ])

    participants = queryset.select_related("bank_account__bank", "channel")

    for p in participants:
        bank_name = ""
        unicef_code = ""
        account_number = ""
        account_name = ""
        validated = ""

        try:
            ba = p.bank_account
            bank_name = ba.bank.name
            unicef_code = ba.bank.unicef_code
            account_number = ba.account_number
            account_name = ba.account_name
            validated = "Yes" if ba.is_validated else "No"
        except BankAccount.DoesNotExist:
            pass

        writer.writerow([
            p.first_name, p.last_name, p.email, p.phone,
            p.channel.name if p.channel else "",
            p.channel_role, p.health_organization,
            p.origin, p.state, p.lga,
            bank_name, unicef_code, account_number,
            account_name, validated,
        ])

    return response
