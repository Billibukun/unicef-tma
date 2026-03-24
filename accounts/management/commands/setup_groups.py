from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

GROUPS = [
    "UNICEF HQ",
    "National Admin",
    "State Admin",
    "M&E Officer",
]


class Command(BaseCommand):
    help = "Create default user groups"

    def handle(self, *args, **options):
        for name in GROUPS:
            group, created = Group.objects.get_or_create(name=name)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {name}")
        self.stdout.write(self.style.SUCCESS("Groups ready."))
