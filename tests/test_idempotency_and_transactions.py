import pytest
from django.db import IntegrityError, transaction

from apps.demandes import services
from apps.demandes.models import Demande, HistoriqueStatut, Statut

from .conftest import NPI

H = "HTTP_IDEMPOTENCY_KEY"


def test_same_key_same_payload_creates_once(usager_client, payload):
    r1 = usager_client.post("/api/demandes/", payload, format="json", **{H: "abc-1"})
    r2 = usager_client.post("/api/demandes/", payload, format="json", **{H: "abc-1"})
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r1.data["id"] == r2.data["id"] and Demande.objects.count() == 1


def test_same_key_different_payload_conflict(usager_client, payload):
    usager_client.post("/api/demandes/", payload, format="json", **{H: "abc-1"})
    r = usager_client.post("/api/demandes/", {**payload, "nombre_copies": 4}, format="json", **{H: "abc-1"})
    assert r.status_code == 409 and Demande.objects.count() == 1


def test_without_key_each_post_creates(usager_client, payload):
    usager_client.post("/api/demandes/", payload, format="json")
    usager_client.post("/api/demandes/", payload, format="json")
    assert Demande.objects.count() == 2


def test_key_is_scoped_per_user(usager_client, agent_client, payload):
    assert usager_client.post("/api/demandes/", payload, format="json", **{H: "k"}).status_code == 201
    assert agent_client.post("/api/demandes/", payload, format="json", **{H: "k"}).status_code == 201


def test_race_on_idempotency_key_falls_back_to_unique_constraint(usager, monkeypatch):
    """Simule deux requêtes concurrentes : le pré-contrôle ne voit rien, la contrainte UNIQUE tranche."""
    first, _ = services.creer_demande(
        acteur=usager, npi=NPI, type_acte="ACTE_NAISSANCE", nombre_copies=1, idempotency_key="race"
    )
    real, calls = services._find_by_key, {"n": 0}

    def blind_first_time(acteur, key):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(acteur, key)

    monkeypatch.setattr(services, "_find_by_key", blind_first_time)
    second, created = services.creer_demande(
        acteur=usager, npi=NPI, type_acte="ACTE_NAISSANCE", nombre_copies=1, idempotency_key="race"
    )
    assert not created and second.pk == first.pk and Demande.objects.count() == 1


def test_transition_is_atomic(usager, agent, monkeypatch):
    d = Demande.objects.create(npi=NPI, type_acte="ACTE_NAISSANCE", nombre_copies=1, created_by=usager)

    def boom(**kwargs):
        raise RuntimeError("panne à mi-chemin")

    monkeypatch.setattr(HistoriqueStatut.objects, "create", boom)
    with pytest.raises(RuntimeError):
        services.changer_statut(demande_id=d.id, nouveau_statut=Statut.EN_COURS, acteur=agent)
    d.refresh_from_db()
    assert d.statut == Statut.DEPOSEE  # rien n'a été enregistré


def test_creation_is_atomic(usager, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("panne")

    monkeypatch.setattr(HistoriqueStatut.objects, "create", boom)
    with pytest.raises(RuntimeError):
        services.creer_demande(acteur=usager, npi=NPI, type_acte="ACTE_NAISSANCE", nombre_copies=1)
    assert Demande.objects.count() == 0


@pytest.mark.parametrize(
    "fields",
    [
        {"nombre_copies": 9},
        {"nombre_copies": 0},
        {"npi": "123"},
        {"statut": "INCONNU"},
        {"type_acte": "PASSEPORT"},
        {"statut": "REJETEE", "motif_rejet": ""},
    ],
)
def test_database_constraints_are_last_line_of_defense(usager, fields):
    base = {"npi": NPI, "type_acte": "ACTE_NAISSANCE", "nombre_copies": 1, "created_by": usager}
    with pytest.raises(IntegrityError), transaction.atomic():
        Demande.objects.create(**{**base, **fields})


def test_error_format_is_structured_and_hides_internals(usager_client):
    r = usager_client.post("/api/demandes/", {}, format="json")
    err = r.json()["error"]
    assert set(err) == {"code", "message", "details"} and "Traceback" not in r.content.decode()
