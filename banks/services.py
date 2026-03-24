import logging
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

from banks.models import Bank, BankAccount

logger = logging.getLogger(__name__)

# NUBAN check-digit weights (repeating pattern for 12 digits)
NUBAN_WEIGHTS = [3, 7, 3, 3, 7, 3, 3, 7, 3, 3, 7, 3]


def validate_nuban(account_number: str, cbn_code: str) -> bool:
    """Validate account number using the NUBAN check-digit algorithm.

    Returns True if the check digit is valid, False otherwise.
    This only checks structure — does NOT confirm the account exists.
    """
    if len(account_number) != 10 or not account_number.isdigit():
        return False

    # For banks with 5+ digit codes, use last 3 digits per CBN spec
    code = cbn_code[-3:] if len(cbn_code) > 3 else cbn_code.zfill(3)

    if len(code) != 3 or not code.isdigit():
        return False

    digits = [int(d) for d in code + account_number[:9]]
    weighted_sum = sum(d * w for d, w in zip(digits, NUBAN_WEIGHTS))
    check_digit = (10 - (weighted_sum % 10)) % 10

    return check_digit == int(account_number[9])


def validate_paystack(account_number: str, cbn_code: str) -> dict:
    """Validate account via Paystack Resolve API.

    Returns dict with keys: success, account_name, error
    """
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        return {"success": False, "account_name": "", "error": "Paystack key not configured"}

    try:
        resp = requests.get(
            "https://api.paystack.co/bank/resolve",
            params={"account_number": account_number, "bank_code": cbn_code},
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200 and data.get("status"):
            return {
                "success": True,
                "account_name": data["data"]["account_name"],
                "error": "",
            }
        return {
            "success": False,
            "account_name": "",
            "error": data.get("message", "Validation failed"),
        }
    except requests.RequestException as e:
        logger.error("Paystack API error: %s", e)
        return {"success": False, "account_name": "", "error": str(e)}


def validate_flutterwave(account_number: str, cbn_code: str) -> dict:
    """Validate account via Flutterwave Resolve API.

    Returns dict with keys: success, account_name, error
    """
    secret_key = settings.FLUTTERWAVE_SECRET_KEY
    if not secret_key:
        return {"success": False, "account_name": "", "error": "Flutterwave key not configured"}

    try:
        resp = requests.post(
            "https://api.flutterwave.com/v3/accounts/resolve",
            json={"account_number": account_number, "account_bank": cbn_code},
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200 and data.get("status") == "success":
            return {
                "success": True,
                "account_name": data["data"]["account_name"],
                "error": "",
            }
        return {
            "success": False,
            "account_name": "",
            "error": data.get("message", "Validation failed"),
        }
    except requests.RequestException as e:
        logger.error("Flutterwave API error: %s", e)
        return {"success": False, "account_name": "", "error": "Could not verify account. Please try again."}


def validate_bank_account(account_number: str, bank: Bank) -> dict:
    """Full validation chain: NUBAN → Paystack → Flutterwave.

    Returns dict with keys: valid, account_name, method, error
    """
    # Step 1: NUBAN structural check (free, instant)
    if not validate_nuban(account_number, bank.cbn_code):
        return {
            "valid": False,
            "account_name": "",
            "method": "nuban",
            "error": "Invalid account number. Please check and try again.",
        }

    # Step 2: Flutterwave API
    result = validate_flutterwave(account_number, bank.cbn_code)
    if result["success"]:
        return {
            "valid": True,
            "account_name": result["account_name"],
            "method": "flutterwave",
            "error": "",
        }

    return {
        "valid": False,
        "account_name": "",
        "method": "flutterwave",
        "error": result["error"],
    }


def validate_and_save(bank_account: BankAccount) -> dict:
    """Validate a BankAccount instance and save the result."""
    result = validate_bank_account(bank_account.account_number, bank_account.bank)

    bank_account.is_validated = result["valid"]
    if result["valid"]:
        bank_account.account_name = result["account_name"]
        bank_account.validation_method = result["method"]
        bank_account.validated_at = timezone.now()
    bank_account.save()

    return result
