from django.core.management.base import BaseCommand

from common.models import State

STATES = [
    ("Abia", "AB"), ("Adamawa", "AD"), ("Akwa Ibom", "AK"), ("Anambra", "AN"),
    ("Bauchi", "BA"), ("Bayelsa", "BY"), ("Benue", "BE"), ("Borno", "BO"),
    ("Cross River", "CR"), ("Delta", "DE"), ("Ebonyi", "EB"), ("Edo", "ED"),
    ("Ekiti", "EK"), ("Enugu", "EN"), ("FCT", "FC"), ("Gombe", "GO"),
    ("Imo", "IM"), ("Jigawa", "JI"), ("Kaduna", "KD"), ("Kano", "KN"),
    ("Katsina", "KT"), ("Kebbi", "KE"), ("Kogi", "KO"), ("Kwara", "KW"),
    ("Lagos", "LA"), ("Nasarawa", "NA"), ("Niger", "NI"), ("Ogun", "OG"),
    ("Ondo", "ON"), ("Osun", "OS"), ("Oyo", "OY"), ("Plateau", "PL"),
    ("Rivers", "RI"), ("Sokoto", "SO"), ("Taraba", "TA"), ("Yobe", "YO"),
    ("Zamfara", "ZA"),
]


class Command(BaseCommand):
    help = "Seed Nigerian states (36 + FCT)"

    def handle(self, *args, **options):
        for name, code in STATES:
            obj, created = State.objects.update_or_create(
                code=code, defaults={"name": name},
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {name} ({code})")
        self.stdout.write(self.style.SUCCESS(f"{len(STATES)} states seeded."))
