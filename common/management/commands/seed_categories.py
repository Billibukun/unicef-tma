from django.core.management.base import BaseCommand

from common.models import ParticipantCategory

CATEGORIES = [
    {"name": "National Trainer", "daily_rate": 0, "description": "National-level trainer/facilitator"},
    {"name": "State Trainer", "daily_rate": 0, "description": "State-level trainer/facilitator"},
    {"name": "Facilitator", "daily_rate": 0, "description": "Training facilitator"},
    {"name": "Participant", "daily_rate": 0, "description": "Training participant"},
    {"name": "Driver", "daily_rate": 0, "description": "Driver"},
    {"name": "UNICEF Staff", "daily_rate": 0, "description": "UNICEF monitoring/oversight staff"},
    {"name": "Observer", "daily_rate": 0, "description": "Observer/monitor"},
]


class Command(BaseCommand):
    help = "Seed participant categories (update DSA rates via Settings)"

    def handle(self, *args, **options):
        for c in CATEGORIES:
            obj, created = ParticipantCategory.objects.update_or_create(
                name=c["name"],
                defaults={"daily_rate": c["daily_rate"], "description": c["description"]},
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {obj.name}")
        self.stdout.write(self.style.SUCCESS("Categories seeded. Set DSA rates in Settings."))
