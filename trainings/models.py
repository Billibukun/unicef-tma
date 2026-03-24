import uuid

from django.conf import settings
from django.db import models


class Training(models.Model):
    MODALITY_CHOICES = [
        ("in_person", "In-Person"),
        ("virtual", "Virtual"),
        ("hybrid", "Hybrid"),
    ]
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    implementing_partner = models.CharField(max_length=300, blank=True)
    responsible_officer = models.CharField(max_length=300, blank=True)
    channel = models.ForeignKey(
        "common.Channel", on_delete=models.PROTECT, related_name="trainings",
    )
    state = models.ForeignKey(
        "common.State", on_delete=models.PROTECT, related_name="trainings",
    )
    destination = models.CharField(max_length=200)
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES, default="in_person")
    training_days = models.PositiveIntegerField(default=1)
    device_management = models.BooleanField(
        default=False, help_text="Enable device tracking for this training",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name="managed_trainings",
        help_text="Users who can manage this training",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_trainings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.title} ({self.state})"

    @property
    def participant_count(self) -> int:
        return self.assignments.count()

    @property
    def total_cost(self):
        total = 0
        for a in self.assignments.select_related("training_category"):
            total += a.total_payment
        return total


class TrainingLevel(models.Model):
    """A level within a training (e.g. State Level, LGA Level)."""
    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, related_name="levels",
    )
    name = models.CharField(max_length=200, help_text="e.g. State Level, LGA Level")
    days = models.PositiveIntegerField(default=1, help_text="Number of training days at this level")
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    class Meta:
        unique_together = ["training", "name"]
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.days}d)"


class TrainingCategory(models.Model):
    """Per-training category with payment columns, belongs to a level."""
    TRAVEL_MODE_CHOICES = [
        ("none", "No Travel"),
        ("road", "Road (Auto-Mileage)"),
        ("air", "Air (Claim-Based)"),
    ]

    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, related_name="categories",
    )
    levels = models.ManyToManyField(
        TrainingLevel, blank=True,
        related_name="categories",
        help_text="Which training level(s) this category participates in",
    )
    name = models.CharField(max_length=200)
    arrival_day = models.BooleanField(
        default=False,
        help_text="Add 1 extra DSA day for arrival (day before training)",
    )
    collect_nin = models.BooleanField(
        default=False,
        help_text="Require NIN during registration",
    )
    is_device_manager = models.BooleanField(
        default=False,
        help_text="People in this category can manage devices for this training",
    )

    # Payment columns
    dsa_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="DSA per day in NGN",
    )
    local_transport = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Local transport allowance (flat)",
    )
    travel_mode = models.CharField(
        max_length=10, choices=TRAVEL_MODE_CHOICES, default="none",
    )
    # terminals comes from training.terminal_fee when travel_mode is air

    # Registration link
    slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration_open = models.BooleanField(default=True)
    registration_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["training", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def total_days(self):
        """Total DSA days = sum of level days + 1 if arrival day."""
        if self.pk:
            total = sum(lv.days for lv in self.levels.all())
            if self.arrival_day:
                total += 1
            return total if total > 0 else 1
        return 1

    @property
    def dsa_total(self):
        return self.dsa_rate * self.total_days

    @property
    def per_person_base(self):
        """Base payment per person (DSA + local transport + terminals if air)."""
        from common.models import SystemSettings
        total = self.dsa_total + self.local_transport
        if self.travel_mode == "air":
            total += SystemSettings.get().terminal_fee_per_leg * 2  # origin + destination
        return total

    @property
    def people_count(self):
        return self.assignments.count()

    @property
    def registration_url(self):
        return f"/participants/register/{self.slug}/"

    @property
    def is_registration_active(self) -> bool:
        if not self.registration_open:
            return False
        if self.registration_expires:
            from django.utils import timezone
            return timezone.now() < self.registration_expires
        return True


class TrainingCluster(models.Model):
    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, related_name="clusters",
    )
    name = models.CharField(max_length=200)
    training_centre = models.CharField(
        max_length=300, blank=True,
        help_text="Venue/location for this cluster",
    )
    lgas = models.ManyToManyField(
        "common.LGA", blank=True, related_name="training_clusters",
    )

    class Meta:
        unique_together = ["training", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TrainingAssignment(models.Model):
    LEG_MODE_CHOICES = [
        ("none", "No Travel"),
        ("road", "Road"),
        ("air", "Air"),
    ]

    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, related_name="assignments",
    )
    participant = models.ForeignKey(
        "participants.Participant", on_delete=models.CASCADE,
        related_name="training_assignments",
    )
    training_category = models.ForeignKey(
        TrainingCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assignments",
    )
    cluster = models.ForeignKey(
        TrainingCluster, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assignments",
    )
    role = models.ForeignKey(
        "common.TrainingRole", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assignments",
    )

    # --- Outbound leg ---
    outbound_mode = models.CharField(
        max_length=10, choices=LEG_MODE_CHOICES, default="none",
    )
    outbound_from = models.ForeignKey(
        "common.State", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    outbound_to = models.ForeignKey(
        "common.State", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    outbound_mileage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outbound_air_claim = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # --- Return leg ---
    return_mode = models.CharField(
        max_length=10, choices=LEG_MODE_CHOICES, default="none",
    )
    return_from = models.ForeignKey(
        "common.State", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    return_to = models.ForeignKey(
        "common.State", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    return_mileage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    return_air_claim = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["training", "participant"]
        ordering = ["training_category__name", "participant__last_name"]

    def __str__(self) -> str:
        return f"{self.participant} → {self.training}"

    # --- Payment calculations (admin-only, never shown to participants) ---

    @property
    def dsa_amount(self):
        if self.training_category:
            return self.training_category.dsa_total
        return 0

    @property
    def transport_amount(self):
        if self.training_category:
            return self.training_category.local_transport
        return 0

    @property
    def terminals_amount(self):
        """Terminal fee: 15k per air leg (house↔airport at each end).
        One air leg = 2 terminals (origin + destination) = 30k.
        Two air legs = 4 terminals = 60k."""
        from common.models import SystemSettings
        fee_per_leg = SystemSettings.get().terminal_fee_per_leg
        terminals = 0
        if self.outbound_mode == "air":
            terminals += 2  # origin terminal + destination terminal
        if self.return_mode == "air":
            terminals += 2
        return fee_per_leg * terminals

    @property
    def outbound_travel_cost(self):
        if self.outbound_mode == "road":
            return self.outbound_mileage
        elif self.outbound_mode == "air":
            return self.outbound_air_claim
        return 0

    @property
    def return_travel_cost(self):
        if self.return_mode == "road":
            return self.return_mileage
        elif self.return_mode == "air":
            return self.return_air_claim
        return 0

    @property
    def travel_amount(self):
        return self.outbound_travel_cost + self.return_travel_cost

    @property
    def total_payment(self):
        return self.dsa_amount + self.transport_amount + self.terminals_amount + self.travel_amount

    def calculate_mileage(self):
        """Auto-calculate road mileage for both legs."""
        from common.mileage import calculate_road_mileage as calc
        from common.models import SystemSettings
        from decimal import Decimal
        rate = SystemSettings.get().mileage_rate_per_km

        if self.outbound_mode == "road" and self.outbound_from and self.outbound_to:
            dist = calc(self.outbound_from.name, self.outbound_to.name, rate)
            self.outbound_mileage = dist / 2  # one way only

        if self.return_mode == "road" and self.return_from and self.return_to:
            dist = calc(self.return_from.name, self.return_to.name, rate)
            self.return_mileage = dist / 2  # one way only
