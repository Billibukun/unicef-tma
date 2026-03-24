from django.db import models


class Participant(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
