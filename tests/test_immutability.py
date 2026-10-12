"""Required test 2: configs, policies, and events cannot be changed after creation."""

import pytest

from control_plane.store import (
    DocumentExistsError,
    ImmutableRecordError,
    Store,
    is_immutable,
)

IMMUTABLE = ["configs", "policies", "reviews", "apps/support-triage/events"]


@pytest.mark.parametrize("collection", IMMUTABLE)
def test_update_raises(any_store: Store, collection: str) -> None:
    any_store.create(collection, "r1", {"v": 1})
    with pytest.raises(ImmutableRecordError):
        any_store.update(collection, "r1", {"v": 2})
    assert any_store.get(collection, "r1") == {"v": 1}


@pytest.mark.parametrize("collection", IMMUTABLE)
def test_overwrite_and_recreate_raise(any_store: Store, collection: str) -> None:
    any_store.create(collection, "r1", {"v": 1})
    with pytest.raises(ImmutableRecordError):
        any_store.set(collection, "r1", {"v": 2})
    with pytest.raises(ImmutableRecordError):
        any_store.create(collection, "r1", {"v": 3})
    assert any_store.get(collection, "r1") == {"v": 1}


@pytest.mark.parametrize("collection", IMMUTABLE)
def test_delete_raises(any_store: Store, collection: str) -> None:
    any_store.create(collection, "r1", {"v": 1})
    with pytest.raises(ImmutableRecordError):
        any_store.delete(collection, "r1")
    assert any_store.get(collection, "r1") == {"v": 1}


@pytest.mark.parametrize("collection", IMMUTABLE)
def test_transaction_cannot_change_immutable(any_store: Store, collection: str) -> None:
    any_store.create(collection, "r1", {"v": 1})

    def overwrite(tx):  # type: ignore[no-untyped-def]
        tx.set(collection, "r1", {"v": 2})

    def update(tx):  # type: ignore[no-untyped-def]
        tx.update(collection, "r1", {"v": 2})

    with pytest.raises(ImmutableRecordError):
        any_store.run_transaction(overwrite)
    with pytest.raises(ImmutableRecordError):
        any_store.run_transaction(update)
    assert any_store.get(collection, "r1") == {"v": 1}


def test_mutable_collections_still_update(any_store: Store) -> None:
    any_store.create("apps", "a1", {"stage": "intake"})
    any_store.update("apps", "a1", {"stage": "business_case"})
    assert any_store.get("apps", "a1") == {"stage": "business_case"}
    with pytest.raises(DocumentExistsError):
        any_store.create("apps", "a1", {"stage": "intake"})


def test_event_subcollections_detected() -> None:
    assert is_immutable("apps/anything/events")
    assert not is_immutable("apps")
    assert not is_immutable("budgets")


def test_collection_group_lists_nested_events(any_store: Store) -> None:
    any_store.create("apps/a1/events", "e1", {"app_id": "a1"})
    any_store.create("apps/a2/events", "e2", {"app_id": "a2"})
    any_store.create("events_other", "x", {"app_id": "zz"})
    assert sorted(d["app_id"] for d in any_store.list_group("events")) == ["a1", "a2"]
