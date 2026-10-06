import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length

models.CharField.register_lookup(Length)


class TypeActe(models.TextChoices):
    NAISSANCE = "ACTE_NAISSANCE", "Acte de naissance"
    CASIER = "CASIER_JUDICIAIRE", "Casier judiciaire"
    RESIDENCE = "CERTIFICAT_RESIDENCE", "Certificat de résidence"


class Statut(models.TextChoices):
    DEPOSEE = "DEPOSEE", "Déposée"
    EN_COURS = "EN_COURS", "En cours de traitement"
    VALIDEE = "VALIDEE", "Validée"
    REJETEE = "REJETEE", "Rejetée"


class Demande(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    npi = models.CharField(max_length=10)
    type_acte = models.CharField(max_length=30, choices=TypeActe.choices)
    nombre_copies = models.PositiveSmallIntegerField()
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.DEPOSEE)
    motif_rejet = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["npi", "-created_at"], name="demande_npi_recent_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(npi__length=10), name="demande_npi_length_10"),
            models.CheckConstraint(
                condition=Q(nombre_copies__gte=1, nombre_copies__lte=5), name="demande_copies_1_5"
            ),
            models.CheckConstraint(condition=Q(statut__in=Statut.values), name="demande_statut_valide"),
            models.CheckConstraint(condition=Q(type_acte__in=TypeActe.values), name="demande_type_valide"),
            # Un rejet est toujours motivé, garanti en base.
            models.CheckConstraint(
                condition=~Q(statut="REJETEE") | ~Q(motif_rejet=""), name="demande_rejet_motive"
            ),
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="demande_idempotency_unique",
            ),
        ]


class HistoriqueStatut(models.Model):
    """Piste d'audit : écrite dans la même transaction que le changement de statut."""

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="historique")
    ancien_statut = models.CharField(max_length=10, null=True, blank=True)
    nouveau_statut = models.CharField(max_length=10)
    acteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    motif = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
