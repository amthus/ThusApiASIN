from rest_framework.throttling import ScopedRateThrottle

from .conftest import NPI, PWD


def test_register_then_login(anon, db):
    r = anon.post("/api/auth/register/", {"npi": NPI, "password": PWD}, format="json")
    assert r.status_code == 201
    assert "password" not in r.data
    r = anon.post("/api/auth/token/", {"username": NPI, "password": PWD}, format="json")
    assert r.status_code == 200 and "access" in r.data and "refresh" in r.data


def test_register_duplicate_npi_conflict(anon, usager):
    r = anon.post("/api/auth/register/", {"npi": NPI, "password": PWD}, format="json")
    assert r.status_code == 409
    assert r.data["error"]["code"] == "conflict"


def test_register_invalid_npi_and_weak_password(anon, db):
    assert anon.post("/api/auth/register/", {"npi": "123", "password": PWD}, format="json").status_code == 400
    assert anon.post("/api/auth/register/", {"npi": NPI, "password": "123"}, format="json").status_code == 400


def test_password_is_hashed(usager):
    assert usager.password != PWD and usager.password.startswith(("md5$", "pbkdf2_sha256$"))


def test_login_wrong_password_401(anon, usager):
    r = anon.post("/api/auth/token/", {"username": NPI, "password": "nope"}, format="json")
    assert r.status_code == 401


def test_protected_endpoint_requires_auth(anon, db):
    assert anon.get("/api/demandes/").status_code == 401
    assert anon.post("/api/demandes/", {}, format="json").status_code == 401


def test_login_is_rate_limited(anon, usager, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "login", "2/min")
    codes = [anon.post("/api/auth/token/", {"username": NPI, "password": "x"}, format="json").status_code for _ in range(3)]
    assert codes == [401, 401, 429]


def test_logout_revokes_refresh_token(anon, usager):
    tokens = anon.post("/api/auth/token/", {"username": NPI, "password": PWD}, format="json").data
    assert anon.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json").status_code == 200
    assert anon.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_login_returns_role_and_npi(anon, usager, agent):
    r = anon.post("/api/auth/token/", {"username": NPI, "password": PWD}, format="json")
    assert (r.data["role"], r.data["npi"]) == ("USAGER", NPI)
    r = anon.post("/api/auth/token/", {"username": "agent1", "password": PWD}, format="json")
    assert (r.data["role"], r.data["npi"]) == ("AGENT", None)
