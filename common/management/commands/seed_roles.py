from django.core.management.base import BaseCommand

from common.models import Channel, TrainingRole

# General roles (no channel — available to all)
GENERAL_ROLES = [
    "National Trainer",
    "State Trainer",
    "Driver",
]

# Channel-specific roles
CHANNEL_ROLES = {
    "npc": ["State ICT", "NPC Focal", "NPC Supervisor", "Data Quality Assessor"],
    "health": ["M&E Officer", "Health Registrar", "Health Supervisor", "DSNO", "LGA M&E"],
    "algon": ["ALGON Focal", "Ward Focal", "Community Mobilizer"],
    "unicef": ["UNICEF Officer", "UNICEF Consultant", "Programme Officer"],
}


class Command(BaseCommand):
    help = "Seed training roles (general + channel-specific)"

    def handle(self, *args, **options):
        # General roles
        for name in GENERAL_ROLES:
            obj, created = TrainingRole.objects.get_or_create(name=name, channel=None)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {name} (General)")

        # Channel-specific
        for code, roles in CHANNEL_ROLES.items():
            try:
                channel = Channel.objects.get(code=code)
            except Channel.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Channel {code} not found, skipping"))
                continue
            for name in roles:
                obj, created = TrainingRole.objects.get_or_create(name=name, channel=channel)
                status = "Created" if created else "Exists"
                self.stdout.write(f"  {status}: {name} ({channel.name})")

        self.stdout.write(self.style.SUCCESS("Training roles seeded."))
