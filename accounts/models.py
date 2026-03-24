from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    channel = models.ForeignKey(
        "common.Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    state = models.ForeignKey(
        "common.State",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    lga = models.ForeignKey(
        "common.LGA",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="LGA",
    )
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.get_full_name() or self.username
