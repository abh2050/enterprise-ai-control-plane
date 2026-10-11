import os

import pytest
from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.fixtures import seed_fixture
from control_plane.settings import Settings
from control_plane.store import FirestoreStore, MemoryStore, Store

LOOPBACK = ("127.0.0.1", 50000)


@pytest.fixture
def memory_store() -> MemoryStore:
    return MemoryStore()


def _stores() -> list[str]:
    names = ["memory"]
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        names.append("firestore")
    return names


@pytest.fixture(params=_stores())
def any_store(request: pytest.FixtureRequest) -> Store:
    if request.param == "memory":
        return MemoryStore()
    import uuid

    # A fresh project id per test isolates emulator data.
    return FirestoreStore(project=f"test-{uuid.uuid4().hex[:12]}")


def make_client(settings: Settings | None = None, store: Store | None = None) -> TestClient:
    store = store or MemoryStore()
    seed_fixture(store)
    app = create_app(settings or Settings(_env_file=None), store)
    return TestClient(app, client=LOOPBACK)
