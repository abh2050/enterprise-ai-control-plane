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
import os
import threading
from collections.abc import Callable
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
        return self._store.get(collection, doc_id)

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        if self._store.get(collection, doc_id) is not None:
            self._raise_exists(collection, doc_id)
        self._writes.append(lambda: self._store.create(collection, doc_id, data))

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        if self._store.get(collection, doc_id) is not None:
            _guard_mutation(collection, doc_id)
        self._writes.append(lambda: self._store.set(collection, doc_id, data))

    def update(self, collection: str, doc_id: str, fields: Doc) -> None:
        _guard_mutation(collection, doc_id)
        if self._store.get(collection, doc_id) is None:
            raise DocumentNotFoundError(f"{collection}/{doc_id}")
        self._writes.append(lambda: self._store.update(collection, doc_id, fields))

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


# Firestore backend


class _FirestoreTransaction:
    def __init__(self, client: Any, tx: Any) -> None:
        self._client = client
        self._tx = tx

    def _ref(self, collection: str, doc_id: str) -> Any:
        return self._client.collection(collection).document(doc_id)

    def get(self, collection: str, doc_id: str) -> Doc | None:
        snap = self._ref(collection, doc_id).get(transaction=self._tx)
        return snap.to_dict() if snap.exists else None

    def create(self, collection: str, doc_id: str, data: Doc) -> None:
        self._tx.create(self._ref(collection, doc_id), data)

    def set(self, collection: str, doc_id: str, data: Doc) -> None:
        if is_immutable(collection):
            # Firestore cannot express "set unless exists" in a transaction write,
            # so create-only collections always use create().
            self._tx.create(self._ref(collection, doc_id), data)
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
        return [s.to_dict() for s in self._client.collection(collection).stream()]

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
        client = self._client

        @self._firestore.transactional  # type: ignore[misc]
        def _run(tx: Any) -> T:
            return fn(_FirestoreTransaction(client, tx))

        result: T = _run(client.transaction())
        return result


def build_store(settings: Settings) -> Store:
    if settings.store_backend is StoreBackend.FIRESTORE:
        return FirestoreStore(settings.gcp_project, settings.firestore_emulator_host)
    return MemoryStore()
