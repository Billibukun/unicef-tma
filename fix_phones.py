"""Normalize all participant phone numbers to 0XXXXXXXXXX format."""
import os
import re

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "tma.settings"
django.setup()

from participants.models import Participant


def normalize_phone(phone):
    if not phone:
        return ""
    # Strip whitespace, quotes
    phone = phone.strip().strip("'\"")
    # Take only first number if slash or 'or'
    phone = re.split(r"[/]|(?:\bor\b)", phone)[0].strip()
    # Remove all non-digit
    digits = re.sub(r"\D", "", phone)
    # +234 prefix
    if digits.startswith("234") and len(digits) >= 13:
        digits = "0" + digits[3:]
    # +1234 typo
    if digits.startswith("1234") and len(digits) >= 14:
        digits = "0" + digits[4:]
    # +12347/8/9 typo
    if len(digits) >= 14 and digits[:4] == "1234":
        digits = "0" + digits[4:]
    # +3249 typo
    if digits.startswith("3249") and len(digits) >= 13:
        digits = "0" + digits[4:]
    # 10 digits starting with 7/8/9 — add leading 0
    if len(digits) == 10 and digits[0] in "789":
        digits = "0" + digits
    # Good: 11 digits starting with 0
    if len(digits) == 11 and digits.startswith("0"):
        return digits
    # Return what we have
    return digits


fixed = 0
unfixable = []
for p in Participant.objects.all():
    old = p.phone or ""
    new = normalize_phone(old)
    if new == old:
        continue
    if len(new) == 11 and new.startswith("0"):
        p.phone = new
        p.save(update_fields=["phone"])
        fixed += 1
    elif new:
        unfixable.append(f'  ID={p.pk} "{old}" -> "{new}" ({p.full_name})')
    elif old.strip():
        unfixable.append(f'  ID={p.pk} EMPTY from "{old}" ({p.full_name})')

print(f"Fixed: {fixed}")
print(f"Unfixable: {len(unfixable)}")
for u in unfixable:
    print(u)
