from django.db import models


class Channel(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LGA(models.Model):
    name = models.CharField(max_length=200)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="lgas")

    class Meta:
        ordering = ["name"]
        verbose_name = "LGA"
        verbose_name_plural = "LGAs"
        unique_together = ["name", "state"]

    def __str__(self) -> str:
        return self.name


class TrainingRole(models.Model):
    """Pre-defined roles that can be assigned in trainings.
    Can be general or channel-specific."""
    name = models.CharField(max_length=100)
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="training_roles",
        help_text="Leave blank for roles that apply across all channels",
    )

    class Meta:
        ordering = ["name"]
        unique_together = ["name", "channel"]

    def __str__(self) -> str:
        if self.channel:
            return f"{self.name} ({self.channel.name})"
        return self.name


class ParticipantCategory(models.Model):
    """Categories like Trainer, Facilitator, Participant, Driver, etc. with DSA rates."""
    name = models.CharField(max_length=100, unique=True)
    daily_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Daily DSA rate in NGN",
    )
    default_days = models.PositiveIntegerField(
        default=1,
        help_text="Default number of training days for this category",
    )
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Participant categories"

    def __str__(self) -> str:
        return f"{self.name} — {self.default_days}d × NGN {self.daily_rate:,.2f}"


class SystemSettings(models.Model):
    """Singleton global settings."""
    mileage_rate_per_km = models.DecimalField(
        max_digits=10, decimal_places=2, default=367,
        help_text="NGN per km for road mileage (round trip auto-calculated)",
    )
    terminal_fee_per_leg = models.DecimalField(
        max_digits=10, decimal_places=2, default=15000,
        help_text="Terminal fee per leg (house↔airport). 15k per leg, so round trip = 30k",
    )

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self) -> str:
        return "System Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "SystemSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
