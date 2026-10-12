"""Required test 12: forged and missing IAP assertions are rejected; valid ones map to the
role stored in the user directory. Keys are generated per test; nothing is mocked except
the public-key fetch, which returns this test's key."""

import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from control_plane.api import create_app
from control_plane.auth import IAP_HEADER
from control_plane.fixtures import seed_registry
from control_plane.iap import KeyCache
from control_plane.settings import IdentityMode, Settings
from control_plane.store import MemoryStore

AUD = "/projects/123/locations/us-central1/services/control-plane"


def keypair() -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private, public


def token(private: str, kid: str, **overrides: object) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://cloud.google.com/iap",
        "aud": AUD,
        "iat": now,
        "exp": now + 600,
        "sub": "accounts.google.com:1",
        "email": "admin@example.com",
        **overrides,
    }
    signer = crypt.ES256Signer.from_string(private, key_id=kid)
    return jwt.encode(signer, claims).decode()


@pytest.fixture
def setup():  # type: ignore[no-untyped-def]
    private, public = keypair()
    store = MemoryStore()
    seed_registry(store)
    app = create_app(
        Settings(_env_file=None, identity_mode=IdentityMode.IAP, iap_audience=AUD), store
    )
    app.state.iap_keys = KeyCache(fetch=lambda: {"k1": public})
    return TestClient(app, client=("10.1.2.3", 443)), private


def me(client: TestClient, assertion: str | None):  # type: ignore[no-untyped-def]
    headers = {IAP_HEADER: assertion} if assertion is not None else {}
    return client.get("/api/me", headers=headers)


def test_valid_assertion_maps_to_stored_role(setup) -> None:  # type: ignore[no-untyped-def]
    client, private = setup
    r = me(client, token(private, "k1"))
    assert r.status_code == 200 and r.json()["role"] == "governance_admin"


def test_missing_and_forged_assertions_rejected(setup) -> None:  # type: ignore[no-untyped-def]
    client, _ = setup
    other_private, _ = keypair()
    assert me(client, None).status_code == 401
    assert me(client, "not-a-jwt").status_code == 401
    assert me(client, token(other_private, "k1")).status_code == 401  # wrong signer
    assert me(client, token(other_private, "unknown-kid")).status_code == 401


@pytest.mark.parametrize(
    "override",
    [
        {"aud": "/projects/999/locations/us-central1/services/other"},
        {"iss": "https://accounts.google.com"},
        {"exp": int(time.time()) - 60, "iat": int(time.time()) - 700},
        {"email": "stranger@example.com"},
    ],
)
def test_wrong_claims_rejected(setup, override) -> None:  # type: ignore[no-untyped-def]
    client, private = setup
    assert me(client, token(private, "k1", **override)).status_code == 401


def test_fixture_header_ignored_in_iap_mode(setup) -> None:  # type: ignore[no-untyped-def]
    client, _ = setup
    r = client.get("/api/me", headers={"X-Fixture-User": "admin@example.com"})
    assert r.status_code == 401
