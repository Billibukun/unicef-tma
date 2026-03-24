from django.core.management.base import BaseCommand

from common.models import Channel

CHANNELS = [
    {"name": "NPC", "code": "npc", "description": "National Population Commission"},
    {"name": "Health", "code": "health", "description": "Health Channel"},
    {"name": "ALGON", "code": "algon", "description": "Association of Local Governments of Nigeria"},
    {"name": "UNICEF", "code": "unicef", "description": "UNICEF Staff (monitoring and oversight)"},
]


class Command(BaseCommand):
    help = "Seed the Channel table with NPC, Health, ALGON, UNICEF"

    def handle(self, *args, **options):
        for ch in CHANNELS:
            obj, created = Channel.objects.update_or_create(
                code=ch["code"],
                defaults={"name": ch["name"], "description": ch["description"]},
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {obj.name}")
        self.stdout.write(self.style.SUCCESS("Channels seeded."))
