"""Logique métier : cycle de vie, idempotence, transactions."""
import logging

from django.db import IntegrityError, transaction
from rest_framework.generics import get_object_or_404

from .exceptions import ConflictError
from .models import Demande, HistoriqueStatut, Statut
from .validators import mask_npi

logger = logging.getLogger(__name__)

TRANSITIONS = {
    Statut.DEPOSEE: {Statut.EN_COURS},
    Statut.EN_COURS: {Statut.VALIDEE, Statut.REJETEE},
}


def _find_by_key(acteur, key):
    return Demande.objects.filter(created_by=acteur, idempotency_key=key).first()


def _replay(existing, npi, type_acte, nombre_copies):
    same = (existing.npi, existing.type_acte, existing.nombre_copies) == (npi, type_acte, nombre_copies)
    if not same:
        raise ConflictError("Cette Idempotency-Key a déjà été utilisée avec un contenu différent.")
    return existing, False


def creer_demande(*, acteur, npi, type_acte, nombre_copies, idempotency_key=None):
    """Retourne (demande, created). Rejouer la même clé avec le même contenu ne crée rien."""
    if idempotency_key:
        existing = _find_by_key(acteur, idempotency_key)
        if existing:
            return _replay(existing, npi, type_acte, nombre_copies)
    try:
        with transaction.atomic():
            demande = Demande.objects.create(
                npi=npi,
                type_acte=type_acte,
                nombre_copies=nombre_copies,
                created_by=acteur,
                idempotency_key=idempotency_key or None,
            )
            HistoriqueStatut.objects.create(demande=demande, nouveau_statut=Statut.DEPOSEE, acteur=acteur)
    except IntegrityError:
        existing = _find_by_key(acteur, idempotency_key) if idempotency_key else None
        if existing is None:
            raise
        return _replay(existing, npi, type_acte, nombre_copies)
    logger.info("demande.creee id=%s npi=%s acteur=%s", demande.id, mask_npi(npi), acteur.pk)
    return demande, True


def changer_statut(*, demande_id, nouveau_statut, acteur, motif=""):
    """Transition atomique ; select_for_update sérialise deux agents agissant en même temps."""
    with transaction.atomic():
        demande = get_object_or_404(Demande.objects.select_for_update(), pk=demande_id)
        if nouveau_statut not in TRANSITIONS.get(demande.statut, set()):
            raise ConflictError(
                f"Transition interdite : une demande « {demande.statut} » ne peut pas passer à « {nouveau_statut} »."
            )
        ancien = demande.statut
        demande.statut = nouveau_statut
        if nouveau_statut == Statut.REJETEE:
            demande.motif_rejet = motif
        demande.save(update_fields=["statut", "motif_rejet", "updated_at"])
        HistoriqueStatut.objects.create(
            demande=demande, ancien_statut=ancien, nouveau_statut=nouveau_statut, acteur=acteur, motif=motif
        )
    logger.info("demande.statut id=%s %s->%s acteur=%s", demande.id, ancien, nouveau_statut, acteur.pk)
    return demande
