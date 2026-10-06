import pytest

from apps.demandes.models import Demande

from .conftest import AUTRE_NPI


def test_usager_creates_demande(usager_client, payload):
    r = usager_client.post("/api/demandes/", payload, format="json")
    assert r.status_code == 201
    assert r.data["statut"] == "DEPOSEE" and r.data["id"]
    assert Demande.objects.count() == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"npi": "123456789"},  # 9 chiffres
        {"npi": "12345678901"},  # 11 chiffres
        {"npi": "12345abcde"},
        {"npi": ""},
        {"type_acte": "PASSEPORT"},
        {"nombre_copies": 0},
        {"nombre_copies": 6},
        {"nombre_copies": "abc"},
        {"nombre_copies": 2.5},
        {"nombre_copies": True},
    ],
)
def test_invalid_input_is_rejected_with_clear_message(usager_client, payload, changes):
    r = usager_client.post("/api/demandes/", {**payload, **changes}, format="json")
    assert r.status_code == 400
    assert r.data["error"]["code"] == "validation_error"
    assert r.data["error"]["details"]
    assert Demande.objects.count() == 0


@pytest.mark.parametrize("missing", ["npi", "type_acte", "nombre_copies"])
def test_missing_field(usager_client, payload, missing):
    payload.pop(missing)
    assert usager_client.post("/api/demandes/", payload, format="json").status_code == 400


def test_usager_cannot_create_for_another_npi(usager_client, payload):
    r = usager_client.post("/api/demandes/", {**payload, "npi": AUTRE_NPI}, format="json")
    assert r.status_code == 403
    assert Demande.objects.count() == 0


def test_agent_can_create_for_any_npi(agent_client, payload):
    r = agent_client.post("/api/demandes/", {**payload, "npi": AUTRE_NPI}, format="json")
    assert r.status_code == 201 and r.data["npi"] == AUTRE_NPI


def test_boundaries_accepted(usager_client, payload):
    for n in (1, 5):
        assert usager_client.post("/api/demandes/", {**payload, "nombre_copies": n}, format="json").status_code == 201


def test_screen_is_served(anon):
    r = anon.get("/")
    assert r.status_code == 200 and b"Nouvelle demande" in r.content
