import uuid

from django.conf import settings
from django.db import models


class Event(models.Model):
    """Parent container grouping Trainings across multiple states/channels."""
    EVENT_TYPE_CHOICES = [
        ("training", "Training"),
        ("monitoring", "Monitoring"),
        ("workshop", "Workshop/Meeting"),
    ]
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("closed", "Closed/Disbursed"),
        ("cancelled", "Cancelled"),
    ]
    TEAM_ROLE_CHOICES = [
        ("lead", "Output Lead"),
        ("support", "Support Team"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default="training")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    # Keep these for backwards compat, but they're being replaced by EventChannel.implementing_partner and EventTeamMember
    implementing_partner = models.CharField(max_length=300, blank=True)
    responsible_officer = models.CharField(max_length=300, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    states = models.ManyToManyField(
        "common.State", blank=True, related_name="events",
    )
    global_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="globally_responsible_events",
        help_text="Overall person responsible for this event",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.title

    @property
    def features(self) -> dict:
        if self.event_type == "training":
            return {"categories": True, "clusters": True, "levels": True, "travel": True,
                    "devices": True, "attendance": True, "registration": True,
                    "forms": False, "reports": False, "payments": True, "banks": True}
        elif self.event_type == "monitoring":
            return {"categories": False, "clusters": False, "levels": False, "travel": False,
                    "devices": False, "attendance": True, "registration": False,
                    "forms": True, "reports": True, "payments": False, "banks": False}
        else:  # workshop
            return {"categories": True, "clusters": False, "levels": False, "travel": True,
                    "devices": False, "attendance": True, "registration": False,
                    "forms": False, "reports": False, "payments": True, "banks": True}

    @property
    def total_participants(self) -> int:
        return sum(t.participant_count for t in self.trainings.all())


class EventChannel(models.Model):
    """Links an Event to a Channel with payment responsibility info."""
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_channels",
    )
    channel = models.ForeignKey(
        "common.Channel", on_delete=models.PROTECT, related_name="event_channels",
    )
    payment_section = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. Field Office, CP Section",
    )
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="responsible_event_channels",
    )
    responsible_name = models.CharField(
        max_length=200, blank=True,
        help_text="Fallback name if responsible person has no user account",
    )
    implementing_partner = models.CharField(
        max_length=300, blank=True,
        help_text="Organization paying for this channel (e.g. NPC HQ ABUJA)",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary payment channel for this event",
    )

    class Meta:
        unique_together = ["event", "channel"]
        ordering = ["channel__name"]

    def __str__(self) -> str:
        return f"{self.event.title} — {self.channel.name}"


class EventTeamMember(models.Model):
    """Team members responsible for managing an event."""
    ROLE_CHOICES = [
        ("lead", "Output Lead"),
        ("support", "Support Team"),
    ]
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="team_members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="event_team_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="support")

    class Meta:
        unique_together = ["event", "user"]
        ordering = ["role", "user__first_name"]

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} ({self.get_role_display()})"


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

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True,
        related_name="trainings",
        help_text="Parent event (null for legacy trainings)",
    )
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
        ("enabled", "Travel Enabled"),
    ]

    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, related_name="categories",
    )
    channel = models.ForeignKey(
        "common.Channel", on_delete=models.PROTECT,
        null=True, blank=True, related_name="training_categories",
        help_text="Override channel (defaults to training's channel if blank)",
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
    device_target_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="managed_by_categories",
        help_text="When assigning devices, only show participants from this category",
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
    short_code = models.CharField(max_length=8, blank=True, db_index=True)
    registration_open = models.BooleanField(default=True)
    registration_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["training", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def effective_channel(self):
        """Channel for this category — own channel or training's channel."""
        return self.channel or self.training.channel

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

    def save(self, *args, **kwargs):
        if not self.short_code:
            import hashlib
            raw = f"{self.slug}{self.name}"
            self.short_code = hashlib.md5(raw.encode()).hexdigest()[:6].upper()
            while TrainingCategory.objects.filter(short_code=self.short_code).exists():
                import secrets
                self.short_code = secrets.token_hex(3).upper()
        super().save(*args, **kwargs)

    @property
    def registration_url(self):
        from django.conf import settings
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        return f"{base}/r/{self.short_code}/"

    @property
    def registration_url_long(self):
        from django.conf import settings
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        return f"{base}/participants/register/{self.slug}/"

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

    attended = models.BooleanField(
        null=True, blank=True, default=None,
        help_text="None=not marked, True=attended, False=did not attend",
    )
    outbound_airline = models.CharField(max_length=100, blank=True)
    return_airline = models.CharField(max_length=100, blank=True)
    outbound_ticket = models.FileField(upload_to="tickets/", blank=True, null=True)
    return_ticket = models.FileField(upload_to="tickets/", blank=True, null=True)
    attended_marked_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
    )
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
        """Local transport × total days (including arrival day if toggled)."""
        if self.training_category:
            return self.training_category.local_transport * self.training_category.total_days
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
