from django.conf import settings
from django.db import models


class Participant(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="participant_profile",
        help_text="System login account (auto-created for device managers)",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    channel = models.ForeignKey(
        "common.Channel",
        on_delete=models.PROTECT,
        related_name="participants",
        help_text="Home channel this person belongs to",
    )
    channel_role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Role within their channel (e.g., State ICT, M&E Officer)",
    )
    health_organization = models.CharField(max_length=200, blank=True)
    origin = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where this person is traveling from",
    )
    state = models.ForeignKey(
        "common.State",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participants",
    )
    lga = models.ForeignKey(
        "common.LGA",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participants",
        verbose_name="LGA",
    )
    ward = models.CharField(max_length=200, blank=True)
    nin = models.CharField(max_length=11, blank=True, verbose_name="NIN")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_participants",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def save(self, *args, **kwargs):
        import re
        self.first_name = self.first_name.upper().strip() if self.first_name else ""
        self.last_name = self.last_name.upper().strip() if self.last_name else ""
        self.email = self.email.lower().strip() if self.email else ""
        # Normalize phone to 0XXXXXXXXXX
        if self.phone:
            phone = self.phone.strip().strip("'\"")
            digits = re.sub(r"\\D", "", phone)
            if digits.startswith("234") and len(digits) >= 13:
                digits = "0" + digits[3:]
            if len(digits) == 10 and digits[0] in "789":
                digits = "0" + digits
            if len(digits) == 11 and digits.startswith("0"):
                self.phone = digits
        super().save(*args, **kwargs)

    @property
    def has_valid_phone(self) -> bool:
        import re
        return bool(self.phone and re.match(r"^0[789]\d{9}$", self.phone))

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def edit_token(self) -> str:
        import hashlib
        import hmac
        secret = settings.SECRET_KEY
        return hmac.new(secret.encode(), str(self.pk).encode(), hashlib.sha256).hexdigest()[:16]

    @property
    def edit_url(self) -> str:
        return f"/participants/{self.pk}/update/{self.edit_token}/"
