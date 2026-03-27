from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Device(models.Model):
    DEVICE_TYPE_CHOICES = [
        ("tablet", "Tablet"),
        ("phone", "Phone"),
        ("laptop", "Laptop"),
    ]
    STATUS_CHOICES = [
        ("available", "Available"),
        ("assigned", "Assigned"),
        ("returned", "Returned"),
        ("damaged", "Damaged"),
        ("lost", "Lost"),
        ("replaced", "Replaced"),
        ("not_working", "Not Working"),
    ]
    CONDITION_CHOICES = [
        ("good", "Working"),
        ("faulty", "Faulty"),
        ("not_working", "Not Working"),
        ("unknown", "Unknown"),
    ]

    serial_number = models.CharField(max_length=100, unique=True)
    imei_1 = models.CharField(max_length=20, blank=True, verbose_name="IMEI 1")
    imei_2 = models.CharField(max_length=20, blank=True, verbose_name="IMEI 2")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES, default="tablet")
    brand = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    assigned_to = models.ForeignKey(
        "participants.Participant",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="devices",
    )
    training = models.ForeignKey(
        "trainings.Training",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="devices",
    )
    state = models.ForeignKey(
        "common.State",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="devices",
    )
    lga = models.ForeignKey(
        "common.LGA",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="devices",
        verbose_name="LGA",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    accessories_complete = models.BooleanField(
        default=True,
        help_text="Are all accessories (charger, case, etc.) present?",
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional notes about this device",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="uploaded_devices",
    )
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="scanned_devices",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_devices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_valid_serial(self) -> bool:
        import re
        return bool(re.match(r'^RT7TITAN\d{7}$', self.serial_number))

    def __str__(self) -> str:
        label = self.brand or self.device_type
        return f"{label} - {self.serial_number}"

    def clean(self):
        if self.imei_1:
            dup = Device.objects.filter(
                models.Q(imei_1=self.imei_1) | models.Q(imei_2=self.imei_1)
            ).exclude(pk=self.pk)
            if dup.exists():
                raise ValidationError({"imei_1": f"IMEI {self.imei_1} already exists on another device."})
        if self.imei_2:
            dup = Device.objects.filter(
                models.Q(imei_1=self.imei_2) | models.Q(imei_2=self.imei_2)
            ).exclude(pk=self.pk)
            if dup.exists():
                raise ValidationError({"imei_2": f"IMEI {self.imei_2} already exists on another device."})


class DeviceLog(models.Model):
    """Track status changes and issues on a device."""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    status = models.CharField(max_length=20, choices=Device.STATUS_CHOICES)
    condition = models.CharField(max_length=20, choices=Device.CONDITION_CHOICES)
    note = models.TextField(blank=True, help_text="What happened, issue description, etc.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="device_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.device.serial_number} — {self.get_status_display()} ({self.created_at:%d %b %Y})"
