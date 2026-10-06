from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length

# Autorise Q(champ__length=10) dans les contraintes CHECK.
models.CharField.register_lookup(Length)


class Role(models.TextChoices):
    USAGER = "USAGER", "Usager"
    AGENT = "AGENT", "Agent"


class User(AbstractUser):
    """Un usager est identifié par son NPI ; un agent n'en a pas."""

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USAGER)
    npi = models.CharField(max_length=10, unique=True, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role="AGENT") | Q(role="USAGER", npi__isnull=False),
                name="usager_requires_npi",
            ),
            models.CheckConstraint(condition=Q(npi__isnull=True) | Q(npi__length=10), name="npi_length_10"),
        ]

    @property
    def is_usager(self) -> bool:
        return self.role == Role.USAGER

    @property
    def is_agent(self) -> bool:
        return self.role == Role.AGENT
