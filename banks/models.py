from django.db import models


class Bank(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    cbn_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="CBN/NIP 3-digit code used by payment APIs",
    )
    unicef_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="UNICEF internal bank code for their payment system",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active banks appear in selection lists",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.short_name or self.name


class BankAccount(models.Model):
    VALIDATION_METHODS = [
        ("nuban", "NUBAN Check-Digit"),
        ("paystack", "Paystack API"),
        ("flutterwave", "Flutterwave API"),
    ]

    participant = models.OneToOneField(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="bank_account",
    )
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=10)
    account_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Account holder name returned by validation API",
    )
    is_proxy = models.BooleanField(
        default=False,
        help_text="This is a colleague's account used on behalf of the participant",
    )
    proxy_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the account owner if this is a proxy account",
    )
    is_validated = models.BooleanField(default=False)
    validation_method = models.CharField(
        max_length=20,
        choices=VALIDATION_METHODS,
        blank=True,
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.account_number} - {self.bank.short_name}"
