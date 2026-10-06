import uuid

import pytest

from apps.demandes.models import Demande, HistoriqueStatut, Statut

from .conftest import NPI


@pytest.fixture
def demande(usager):
    return Demande.objects.create(npi=NPI, type_acte="CASIER_JUDICIAIRE", nombre_copies=1, created_by=usager)


def url(d, action):
    return f"/api/demandes/{d.id}/{action}/"


def test_full_happy_path(agent_client, demande):
    assert agent_client.post(url(demande, "prendre-en-charge")).data["statut"] == "EN_COURS"
    assert agent_client.post(url(demande, "valider")).data["statut"] == "VALIDEE"
    assert HistoriqueStatut.objects.filter(demande=demande).count() == 2


def test_rejection_requires_motif(agent_client, demande):
    agent_client.post(url(demande, "prendre-en-charge"))
    assert agent_client.post(url(demande, "rejeter"), {}, format="json").status_code == 400
    assert agent_client.post(url(demande, "rejeter"), {"motif": "   "}, format="json").status_code == 400
    demande.refresh_from_db()
    assert demande.statut == Statut.EN_COURS


def test_rejection_with_motif(agent_client, demande):
    agent_client.post(url(demande, "prendre-en-charge"))
    r = agent_client.post(url(demande, "rejeter"), {"motif": "Pièce illisible"}, format="json")
    assert r.status_code == 200 and r.data["statut"] == "REJETEE" and r.data["motif_rejet"] == "Pièce illisible"


@pytest.mark.parametrize("action", ["valider", "rejeter"])
def test_cannot_skip_en_cours(agent_client, demande, action):
    r = agent_client.post(url(demande, action), {"motif": "x"}, format="json")
    assert r.status_code == 409
    assert "Transition interdite" in r.data["error"]["message"]


@pytest.mark.parametrize("final", ["valider", "rejeter"])
@pytest.mark.parametrize("action", ["prendre-en-charge", "valider", "rejeter"])
def test_final_states_never_change(agent_client, demande, final, action):
    agent_client.post(url(demande, "prendre-en-charge"))
    agent_client.post(url(demande, final), {"motif": "x"}, format="json")
    before = Demande.objects.get(pk=demande.pk).statut
    assert agent_client.post(url(demande, action), {"motif": "y"}, format="json").status_code == 409
    assert Demande.objects.get(pk=demande.pk).statut == before


def test_usager_cannot_transition(usager_client, demande):
    assert usager_client.post(url(demande, "prendre-en-charge")).status_code == 403


def test_anonymous_cannot_transition(anon, demande):
    assert anon.post(url(demande, "prendre-en-charge")).status_code == 401


def test_unknown_demande_404(agent_client):
    assert agent_client.post(f"/api/demandes/{uuid.uuid4()}/valider/").status_code == 404
    assert agent_client.post("/api/demandes/not-a-uuid/valider/").status_code == 404


def test_detail_idor_protection(autre_client, usager_client, demande):
    assert autre_client.get(f"/api/demandes/{demande.id}/").status_code == 404
    r = usager_client.get(f"/api/demandes/{demande.id}/")
    assert r.status_code == 200 and r.data["id"] == str(demande.id) and r.data["historique"] == []
