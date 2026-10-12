import os

import pytest
from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.fixtures import seed_registry
from control_plane.settings import Settings
from control_plane.store import FileStore, FirestoreStore, MemoryStore, Store

LOOPBACK = ("127.0.0.1", 50000)


@pytest.fixture
def memory_store() -> MemoryStore:
    return MemoryStore()


def _stores() -> list[str]:
    names = ["memory", "file"]
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        names.append("firestore")
    return names


@pytest.fixture(params=_stores())
def any_store(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Store:
    if request.param == "memory":
        return MemoryStore()
    if request.param == "file":
        return FileStore(tmp_path_factory.mktemp("store"))
    import uuid

    # A fresh project id per test isolates emulator data.
    return FirestoreStore(project=f"test-{uuid.uuid4().hex[:12]}")


def make_client(settings: Settings | None = None, store: Store | None = None) -> TestClient:
    store = store or MemoryStore()
    seed_registry(store)
    app = create_app(settings or Settings(_env_file=None), store)
    return TestClient(app, client=LOOPBACK)
