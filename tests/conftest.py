import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.users.models import Role, User

PWD = "Str0ng-Test-Pass!42"
NPI = "1234567890"
AUTRE_NPI = "0987654321"


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()


def _client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def usager(db):
    return User.objects.create_user(username=NPI, npi=NPI, role=Role.USAGER, password=PWD)


@pytest.fixture
def autre_usager(db):
    return User.objects.create_user(username=AUTRE_NPI, npi=AUTRE_NPI, role=Role.USAGER, password=PWD)


@pytest.fixture
def agent(db):
    return User.objects.create_user(username="agent1", role=Role.AGENT, password=PWD)


@pytest.fixture
def anon():
    return APIClient()


@pytest.fixture
def usager_client(usager):
    return _client_for(usager)


@pytest.fixture
def autre_client(autre_usager):
    return _client_for(autre_usager)


@pytest.fixture
def agent_client(agent):
    return _client_for(agent)


@pytest.fixture
def payload():
    return {"npi": NPI, "type_acte": "ACTE_NAISSANCE", "nombre_copies": 2}
