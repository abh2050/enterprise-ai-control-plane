"""Document storage. This is the only module that talks to Firestore.

Two backends share one interface:
- ``MemoryStore`` runs with no dependencies, for local development and fast tests.
- ``FirestoreStore`` runs against the Firestore emulator or a real project.

Configs, policies, reviews, and app events are create only. The store refuses to
update, overwrite, or delete them. A database administrator with direct access can
still alter these records; the guarantee covers application code paths only.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol, TypeVar

from control_plane.settings import Settings, StoreBackend

Doc = dict[str, Any]
T = TypeVar("T")

IMMUTABLE_COLLECTIONS = frozenset({"configs", "policies", "reviews", "events"})


class StoreError(Exception):
    pass


class ImmutableRecordError(StoreError):
    """Raised when code tries to change a create-only record."""


class DocumentExistsError(StoreError):
    pass


class DocumentNotFoundError(StoreError):
    pass


def _leaf(collection: str) -> str:
    """Last segment of a collection path, e.g. ``apps/a1/events`` -> ``events``."""
    return collection.rstrip("/").rsplit("/", 1)[-1]


def is_immutable(collection: str) -> bool:
    return _leaf(collection) in IMMUTABLE_COLLECTIONS


def _guard_mutation(collection: str, doc_id: str) -> None:
    if is_immutable(collection):
        raise ImmutableRecordError(f"{collection}/{doc_id} is create only")


class Transaction(Protocol):
    """Reads must happen before writes, matching Firestore transaction rules."""

    def get(self, collection: str, doc_id: str) -> Doc | None: ...
    def create(self, collection: str, doc_id: str, data: Doc) -> None: ...
    def set(self, collection: str, doc_id: str, data: Doc) -> None: ...
    def update(self, collection: str, doc_id: str, fields: Doc) -> None: ...


class Store(Protocol):
    def get(self, collection: str, doc_id: str) -> Doc | None: ...
    def list(self, collection: str) -> list[Doc]: ...
    def create(self, collection: str, doc_id: str, data: Doc) -> None: ...
    def set(self, collection: str, doc_id: str, data: Doc) -> None: ...
    def update(self, collection: str, doc_id: str, fields: Doc) -> None: ...
    def delete(self, collection: str, doc_id: str) -> None: ...
    def run_transaction(self, fn: Callable[[Transaction], T]) -> T: ...


# Memory backend


class _MemoryTransaction:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store
        self._writes: list[Callable[[], None]] = []

    def get(self, collection: str, doc_id: str) -> Doc | None:
        if self._writes:
            raise StoreError("transaction reads must happen before writes")
        return MemoryStore.get(self._store, collection, doc_id)

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        if MemoryStore.get(self._store, collection, doc_id) is not None:
            self._raise_exists(collection, doc_id)
        self._writes.append(lambda: MemoryStore.create(self._store, collection, doc_id, data))

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        if MemoryStore.get(self._store, collection, doc_id) is not None:
            _guard_mutation(collection, doc_id)
        self._writes.append(lambda: MemoryStore.set(self._store, collection, doc_id, data))

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        _guard_mutation(collection, doc_id)
        if MemoryStore.get(self._store, collection, doc_id) is None:
            raise DocumentNotFoundError(f"{collection}/{doc_id}")
        self._writes.append(lambda: MemoryStore.update(self._store, collection, doc_id, fields))

    @staticmethod
    def _raise_exists(collection: str, doc_id: str) -> None:
        if is_immutable(collection):
            raise ImmutableRecordError(f"{collection}/{doc_id} already exists")
        raise DocumentExistsError(f"{collection}/{doc_id}")

    def commit(self) -> None:
        for write in self._writes:
            write()


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Doc]] = {}
        self._lock = threading.RLock()

    def get(self, collection: str, doc_id: str) -> Doc | None:
        with self._lock:
            doc = self._data.get(collection, {}).get(doc_id)
            return copy.deepcopy(doc) if doc is not None else None

    def list(self, collection: str) -> list[Doc]:
        with self._lock:
            return [copy.deepcopy(d) for d in self._data.get(collection, {}).values()]

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        with self._lock:
            docs = self._data.setdefault(collection, {})
            if doc_id in docs:
                _MemoryTransaction._raise_exists(collection, doc_id)
            docs[doc_id] = copy.deepcopy(data)

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        with self._lock:
            docs = self._data.setdefault(collection, {})
            if doc_id in docs:
                _guard_mutation(collection, doc_id)
            docs[doc_id] = copy.deepcopy(data)

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        _guard_mutation(collection, doc_id)
        with self._lock:
            docs = self._data.get(collection, {})
            if doc_id not in docs:
                raise DocumentNotFoundError(f"{collection}/{doc_id}")
            docs[doc_id].update(copy.deepcopy(fields))

    def delete(self, collection: str, doc_id: str) -> None:
        _guard_mutation(collection, doc_id)
        with self._lock:
            self._data.get(collection, {}).pop(doc_id, None)

    def run_transaction(self, fn: Callable[[Transaction], T]) -> T:
        # One lock serializes transactions, which is stricter than Firestore's
        # optimistic concurrency and gives the same admission guarantees.
        with self._lock:
            tx = _MemoryTransaction(self)
            result = fn(tx)
            tx.commit()
            return result


# File backend


class FileStore(MemoryStore):
    """MemoryStore persisted to one JSON file, safe across processes on one machine.

    Every write and every transaction holds an exclusive file lock, reloads the latest
    state, applies the change, and replaces the file atomically. Paid local runs use it
    so the budget ledger survives between commands.
    """

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        super().__init__()
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "store.json"
        self._lock_path = self._dir / "store.lock"
        self._reload()

    def _reload(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def _persist(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data))
        os.replace(tmp, self._path)

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        with self._lock, self._lock_path.open("a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                self._reload()
                yield
                self._persist()
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def get(self, collection: str, doc_id: str) -> Doc | None:
        with self._lock:
            self._reload()
            return super().get(collection, doc_id)

    def list(self, collection: str) -> list[Doc]:
        with self._lock:
            self._reload()
            return super().list(collection)

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        with self._exclusive():
            super().create(collection, doc_id, data)

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        with self._exclusive():
            super().set(collection, doc_id, data)

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        _guard_mutation(collection, doc_id)
        with self._exclusive():
            super().update(collection, doc_id, fields)

    def delete(self, collection: str, doc_id: str) -> None:
        _guard_mutation(collection, doc_id)
        with self._exclusive():
            super().delete(collection, doc_id)

    def run_transaction(self, fn: Callable[[Transaction], T]) -> T:
        with self._exclusive():
            tx = _MemoryTransaction(self)
            result = fn(tx)
            # Commit through the in-memory methods; _exclusive persists on exit.
            for write in tx._writes:
                write()
            return result


# Firestore backend


class _FirestoreTransaction:
    def __init__(self, client: Any, tx: Any) -> None:
        self._client = client
        self._tx = tx
        self.created: list[str] = []

    def _ref(self, collection: str, doc_id: str) -> Any:
        return self._client.collection(collection).document(doc_id)

    def get(self, collection: str, doc_id: str) -> Doc | None:
        snap = self._ref(collection, doc_id).get(transaction=self._tx)
        return snap.to_dict() if snap.exists else None

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        self.created.append(collection)
        self._tx.create(self._ref(collection, doc_id), data)

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        if is_immutable(collection):
            # Firestore cannot express "set unless exists" in a transaction write,
            # so create-only collections always use create().
            self.create(collection, doc_id, data)
        else:
            self._tx.set(self._ref(collection, doc_id), data)

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        _guard_mutation(collection, doc_id)
        self._tx.update(self._ref(collection, doc_id), fields)


class FirestoreStore:
    def __init__(self, project: str, emulator_host: str | None = None) -> None:
        if emulator_host:
            os.environ["FIRESTORE_EMULATOR_HOST"] = emulator_host
        from google.cloud import firestore

        self._firestore = firestore
        self._client = firestore.Client(project=project)

    def _ref(self, collection: str, doc_id: str) -> Any:
        return self._client.collection(collection).document(doc_id)

    def get(self, collection: str, doc_id: str) -> Doc | None:
        snap = self._ref(collection, doc_id).get()
        return snap.to_dict() if snap.exists else None

    def list(self, collection: str) -> list[Doc]:
        snaps = self._client.collection(collection).stream()
        return [d for s in snaps if (d := s.to_dict()) is not None]

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        from google.api_core.exceptions import AlreadyExists

        try:
            self._ref(collection, doc_id).create(data)
        except AlreadyExists as exc:
            if is_immutable(collection):
                raise ImmutableRecordError(f"{collection}/{doc_id} already exists") from exc
            raise DocumentExistsError(f"{collection}/{doc_id}") from exc

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        if is_immutable(collection):
            self.create(collection, doc_id, data)
            return
        self._ref(collection, doc_id).set(data)

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        from google.api_core.exceptions import NotFound

        _guard_mutation(collection, doc_id)
        try:
            self._ref(collection, doc_id).update(fields)
        except NotFound as exc:
            raise DocumentNotFoundError(f"{collection}/{doc_id}") from exc

    def delete(self, collection: str, doc_id: str) -> None:
        _guard_mutation(collection, doc_id)
        self._ref(collection, doc_id).delete()

    def run_transaction(self, fn: Callable[[Transaction], T]) -> T:
        from google.api_core.exceptions import AlreadyExists

        client = self._client
        wrappers: list[_FirestoreTransaction] = []

        @self._firestore.transactional
        def _run(tx: Any) -> T:
            wrapper = _FirestoreTransaction(client, tx)
            wrappers.append(wrapper)
            return fn(wrapper)

        try:
            result: T = _run(client.transaction())
        except AlreadyExists as exc:
            # Firestore reports a create conflict at commit, without naming the document.
            created = wrappers[-1].created if wrappers else []
            if any(is_immutable(c) for c in created):
                raise ImmutableRecordError(
                    "transaction tried to recreate a create-only record"
                ) from exc
            raise DocumentExistsError("transaction tried to create an existing document") from exc
        return result


def build_store(settings: Settings) -> Store:
    if settings.store_backend is StoreBackend.FIRESTORE:
        return FirestoreStore(settings.gcp_project, settings.firestore_emulator_host)
    if settings.store_backend is StoreBackend.FILE:
        return FileStore(settings.file_store_dir)
    return MemoryStore()
