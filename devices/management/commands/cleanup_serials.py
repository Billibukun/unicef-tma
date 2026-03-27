"""Find and flag devices with invalid serial numbers (not matching RT7TITAN + 7 digits)."""
import re

from django.core.management.base import BaseCommand

from devices.models import Device


VALID_SERIAL = re.compile(r'^RT7TITAN\d{7}$')


class Command(BaseCommand):
    help = "List devices with invalid serial numbers and optionally prefix them with INVALID_"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Prefix invalid serials with INVALID_ so they're easy to find and re-scan",
        )

    def handle(self, *args, **options):
        invalid = []
        for d in Device.objects.all():
            if not VALID_SERIAL.match(d.serial_number):
                invalid.append(d)

        if not invalid:
            self.stdout.write(self.style.SUCCESS("All serial numbers are valid."))
            return

        self.stdout.write(self.style.WARNING(f"\n{len(invalid)} device(s) with invalid serial numbers:\n"))
        for d in invalid:
            lga = d.lga.name if d.lga else "—"
            scanned = d.scanned_by.username if d.scanned_by else (d.uploaded_by.username if d.uploaded_by else "—")
            self.stdout.write(
                f"  ID={d.pk}  S/N=\"{d.serial_number}\"  IMEI1={d.imei_1 or '—'}  "
                f"LGA={lga}  ScannedBy={scanned}  Date={d.created_at:%Y-%m-%d}"
            )

        if options["fix"]:
            self.stdout.write("")
            for d in invalid:
                old = d.serial_number
                d.serial_number = f"INVALID_{d.pk}_{old[:20]}"
                d.save(update_fields=["serial_number"])
                self.stdout.write(f"  Renamed: \"{old}\" -> \"{d.serial_number}\"")
            self.stdout.write(self.style.SUCCESS(
                f"\nDone. {len(invalid)} device(s) flagged. Device managers can find and re-scan them."
            ))
        else:
            self.stdout.write(self.style.NOTICE(
                "\nRun with --fix to prefix invalid serials with INVALID_"
            ))
