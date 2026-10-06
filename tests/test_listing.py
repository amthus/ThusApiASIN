from apps.demandes.models import Demande, Statut

from .conftest import AUTRE_NPI, NPI


def _mk(user, npi=NPI, statut=Statut.DEPOSEE, n=1):
    for _ in range(n):
        Demande.objects.create(npi=npi, type_acte="ACTE_NAISSANCE", nombre_copies=1, statut=statut, created_by=user)


def test_list_most_recent_first(usager, usager_client, payload):
    ids = [usager_client.post("/api/demandes/", payload, format="json").data["id"] for _ in range(3)]
    r = usager_client.get("/api/demandes/")
    assert [d["id"] for d in r.data["results"]] == ids[::-1]


def test_filter_by_statut(usager, usager_client):
    _mk(usager)
    _mk(usager, statut=Statut.EN_COURS, n=2)
    r = usager_client.get("/api/demandes/?statut=EN_COURS")
    assert r.data["count"] == 2 and all(d["statut"] == "EN_COURS" for d in r.data["results"])


def test_invalid_statut_filter_400(usager_client):
    assert usager_client.get("/api/demandes/?statut=NOPE").status_code == 400


def test_invalid_npi_filter_400(agent_client):
    assert agent_client.get("/api/demandes/?npi=12").status_code == 400


def test_usager_only_sees_own(usager, autre_usager, usager_client):
    _mk(usager)
    _mk(autre_usager, npi=AUTRE_NPI, n=3)
    assert usager_client.get("/api/demandes/").data["count"] == 1


def test_usager_cannot_list_other_npi(usager_client):
    assert usager_client.get(f"/api/demandes/?npi={AUTRE_NPI}").status_code == 403


def test_agent_lists_by_npi(agent_client, usager, autre_usager):
    _mk(usager)
    _mk(autre_usager, npi=AUTRE_NPI, n=2)
    assert agent_client.get(f"/api/demandes/?npi={AUTRE_NPI}").data["count"] == 2


def test_pagination_max_20(usager, usager_client):
    _mk(usager, n=25)
    p1 = usager_client.get("/api/demandes/").data
    assert p1["count"] == 25 and len(p1["results"]) == 20
    assert len(usager_client.get("/api/demandes/?page=2").data["results"]) == 5
    assert len(usager_client.get("/api/demandes/?page_size=100").data["results"]) == 20


def test_stats_per_status(usager, autre_usager, usager_client):
    _mk(usager, n=2)
    _mk(usager, statut=Statut.VALIDEE)
    _mk(autre_usager, npi=AUTRE_NPI, n=5)
    r = usager_client.get("/api/demandes/stats/")
    assert r.data == {"total": 3, "par_statut": {"DEPOSEE": 2, "EN_COURS": 0, "VALIDEE": 1, "REJETEE": 0}}


def test_list_has_no_n_plus_one(usager, usager_client, django_assert_max_num_queries):
    _mk(usager, n=15)
    with django_assert_max_num_queries(3):
        usager_client.get("/api/demandes/")
