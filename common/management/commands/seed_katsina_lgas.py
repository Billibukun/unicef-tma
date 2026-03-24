from django.core.management.base import BaseCommand

from common.models import LGA, State

LGAS = [
    "Bakori", "Batagarawa", "Batsari", "Baure", "Bindawa", "Charanchi",
    "Dan Musa", "Dandume", "Danja", "Daura", "Dutsi", "Dutsin-Ma",
    "Faskari", "Funtua", "Ingawa", "Jibia", "Kafur", "Kaita", "Kankara",
    "Kankia", "Katsina", "Kurfi", "Kusada", "Mai'Adua", "Malumfashi",
    "Mani", "Mashi", "Matazu", "Musawa", "Rimi", "Sabuwa", "Safana",
    "Sandamu", "Zango",
]


class Command(BaseCommand):
    help = "Seed the 34 LGAs of Katsina State"

    def handle(self, *args, **options):
        state = State.objects.get(code="KT")

        for name in LGAS:
            _, created = LGA.objects.update_or_create(
                state=state, name=name,
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {name}")

        self.stdout.write(self.style.SUCCESS(f"{len(LGAS)} Katsina LGAs seeded."))
