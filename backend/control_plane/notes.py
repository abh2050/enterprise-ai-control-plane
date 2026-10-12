"""Governance notes on an app (console spec Section 9, Applications page).

- Plain text up to 5,000 characters, stamped by the server with time and author.
- An idempotency key makes a repeated submission return the first note, not a second.
- Authors may edit for 15 minutes; every prior version is kept.
- Deletion is soft and requires a reason.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from control_plane.registry import ForbiddenError, NotFoundError, RegistryError
from control_plane.store import Store, Transaction

MAX_CHARS = 5000
EDIT_WINDOW = timedelta(minutes=15)


def _clean(text: str) -> str:
    text = text.strip()
    if not text:
        raise RegistryError("a note cannot be empty")
    if len(text) > MAX_CHARS:
        raise RegistryError(f"notes are limited to {MAX_CHARS:,} characters")
    return text


def create_note(
    store: Store,
    app_id: str,
    author: str,
    text: str,
    idempotency_key: str,
    now: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    """Return (note, created). A repeated idempotency key returns the original note."""
    now = now or datetime.now(UTC)
    body = _clean(text)
    if not idempotency_key or len(idempotency_key) > 100:
        raise RegistryError("an idempotency key is required")
    note_id = f"{app_id}__{idempotency_key}"

    def go(tx: Transaction) -> tuple[dict[str, Any], bool]:
        existing = tx.get("notes", note_id)
        if existing is not None:
            return existing, False
        if tx.get("apps", app_id) is None:
            raise NotFoundError(f"app {app_id} not found")
        note: dict[str, Any] = {
            "note_id": note_id,
            "app_id": app_id,
            "author": author,
            "text": body,
            "created_at": now.isoformat(),
            "edited_at": None,
            "history": [],
            "deleted_at": None,
            "deleted_by": None,
            "delete_reason": None,
        }
        tx.set("notes", note_id, note)
        event_id = uuid.uuid4().hex
        tx.create(
            f"apps/{app_id}/events",
            event_id,
            {
                "event_id": event_id,
                "app_id": app_id,
                "kind": "note_added",
                "from_stage": None,
                "to_stage": None,
                "actor": author,
                "reason": "Governance note added",
                "evidence_refs": [f"notes/{note_id}"],
                "created_at": now.isoformat(),
            },
        )
        return note, True

    return store.run_transaction(go)


def edit_note(
    store: Store, note_id: str, author: str, text: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    body = _clean(text)

    def go(tx: Transaction) -> dict[str, Any]:
        note = tx.get("notes", note_id)
        if note is None or note.get("deleted_at"):
            raise NotFoundError("note not found")
        if note["author"] != author:
            raise ForbiddenError("Only the author can edit a note")
        if now - datetime.fromisoformat(note["created_at"]) > EDIT_WINDOW:
            raise ForbiddenError("Notes can be edited for 15 minutes after they are saved")
        history = [*note["history"], {"text": note["text"], "until": now.isoformat()}]
        updates = {"text": body, "edited_at": now.isoformat(), "history": history}
        tx.update("notes", note_id, updates)
        return {**note, **updates}

    return store.run_transaction(go)


def delete_note(
    store: Store, note_id: str, actor: str, role: str, reason: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    if not reason.strip():
        raise RegistryError("deleting a note requires a reason")

    def go(tx: Transaction) -> dict[str, Any]:
        note = tx.get("notes", note_id)
        if note is None or note.get("deleted_at"):
            raise NotFoundError("note not found")
        if note["author"] != actor and role != "governance_admin":
            raise ForbiddenError("Only the author or a governance admin can delete a note")
        updates = {"deleted_at": now.isoformat(), "deleted_by": actor, "delete_reason": reason}
        tx.update("notes", note_id, updates)
        return {**note, **updates}

    return store.run_transaction(go)


def list_notes(store: Store, app_id: str) -> list[dict[str, Any]]:
    notes = [n for n in store.list("notes") if n["app_id"] == app_id and not n["deleted_at"]]
    return sorted(notes, key=lambda n: n["created_at"])
