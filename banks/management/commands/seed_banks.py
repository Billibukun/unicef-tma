from django.core.management.base import BaseCommand

from banks.models import Bank

# Banks from UNICEF's official bank codes sheet (September 2024)
# cbn_code = CBN/NIP code (used by Flutterwave/Paystack APIs)
# unicef_code = UNICEF BANKID (used in their payment exports)
BANKS = [
    {"name": "First Bank of Nigeria", "short_name": "FirstBank", "cbn_code": "011", "unicef_code": "11153166"},
    {"name": "Citibank Nigeria Limited", "short_name": "Citibank", "cbn_code": "023", "unicef_code": "23150034"},
    {"name": "Heritage Bank Plc", "short_name": "Heritage", "cbn_code": "030", "unicef_code": "30150014"},
    {"name": "Union Bank of Nigeria", "short_name": "Union Bank", "cbn_code": "032", "unicef_code": "32080425"},
    {"name": "United Bank for Africa", "short_name": "UBA", "cbn_code": "033", "unicef_code": "33152666"},
    {"name": "Wema Bank Plc", "short_name": "Wema", "cbn_code": "035", "unicef_code": "35340159"},
    {"name": "Access Bank Plc", "short_name": "Access Bank", "cbn_code": "044", "unicef_code": "44150039"},
    {"name": "Ecobank Nigeria", "short_name": "Ecobank", "cbn_code": "050", "unicef_code": "50150311"},
    {"name": "Zenith Bank Plc", "short_name": "Zenith", "cbn_code": "057", "unicef_code": "57020046"},
    {"name": "Guaranty Trust Bank", "short_name": "GTBank", "cbn_code": "058", "unicef_code": "58152049"},
    {"name": "Standard Chartered Bank", "short_name": "StanChart", "cbn_code": "068", "unicef_code": "68120016"},
    {"name": "Fidelity Bank Plc", "short_name": "Fidelity", "cbn_code": "070", "unicef_code": "70020926"},
    {"name": "Polaris Bank Limited", "short_name": "Polaris", "cbn_code": "076", "unicef_code": "76151365"},
    {"name": "Keystone Bank Limited", "short_name": "Keystone", "cbn_code": "082", "unicef_code": "82150033"},
    {"name": "SunTrust Bank Nigeria", "short_name": "SunTrust", "cbn_code": "100", "unicef_code": "100152041"},
    {"name": "Providus Bank Limited", "short_name": "Providus", "cbn_code": "101", "unicef_code": "101152019"},
    {"name": "Titan Trust Bank", "short_name": "Titan", "cbn_code": "102", "unicef_code": "102150010"},
    {"name": "Globus Bank Limited", "short_name": "Globus", "cbn_code": "103", "unicef_code": "103150019"},
    {"name": "Parallex Bank Limited", "short_name": "Parallex", "cbn_code": "104", "unicef_code": "104150005"},
    {"name": "Premium Trust Bank", "short_name": "PremiumTrust", "cbn_code": "105", "unicef_code": "105150004"},
    {"name": "First City Monument Bank", "short_name": "FCMB", "cbn_code": "214", "unicef_code": "214159996"},
    {"name": "Unity Bank Plc", "short_name": "Unity", "cbn_code": "215", "unicef_code": "215203634"},
    {"name": "Stanbic IBTC Bank Plc", "short_name": "Stanbic", "cbn_code": "221", "unicef_code": "221159522"},
    {"name": "Sterling Bank Plc", "short_name": "Sterling", "cbn_code": "232", "unicef_code": "232150032"},
    {"name": "Jaiz Bank Plc", "short_name": "Jaiz", "cbn_code": "301", "unicef_code": "301080020"},
    {"name": "TAJ Bank", "short_name": "TAJ", "cbn_code": "302", "unicef_code": "302080016"},
    {"name": "Lotus Bank", "short_name": "Lotus", "cbn_code": "303", "unicef_code": "303150013"},
    {"name": "FSDH Merchant Bank", "short_name": "FSDH", "cbn_code": "501", "unicef_code": "501150019"},
    {"name": "Coronation Merchant Bank", "short_name": "Coronation", "cbn_code": "559", "unicef_code": "559159994"},
    {"name": "Nova Merchant Bank", "short_name": "Nova", "cbn_code": "561", "unicef_code": "561150017"},
]


class Command(BaseCommand):
    help = "Seed Nigerian banks with CBN codes and UNICEF BANKID codes"

    def handle(self, *args, **options):
        for b in BANKS:
            obj, created = Bank.objects.update_or_create(
                cbn_code=b["cbn_code"],
                defaults={
                    "name": b["name"],
                    "short_name": b["short_name"],
                    "unicef_code": b["unicef_code"],
                },
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {obj.short_name} ({obj.cbn_code}) -> UNICEF: {obj.unicef_code}")

        # Remove Optimus (was in old seed but not in UNICEF list)
        removed = Bank.objects.filter(cbn_code="107").delete()[0]
        if removed:
            self.stdout.write("  Removed: Optimus (not in UNICEF bank list)")

        self.stdout.write(self.style.SUCCESS(f"{len(BANKS)} banks seeded with UNICEF codes."))
