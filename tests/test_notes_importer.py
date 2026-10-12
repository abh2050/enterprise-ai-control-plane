from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from control_plane.importer import import_csv
from control_plane.notes import create_note, delete_note, edit_note, list_notes
from control_plane.portfolio import safe_cell
from control_plane.registry import ForbiddenError, RegistryError
from control_plane.store import MemoryStore, Store

NOW = datetime(2026, 10, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


def store_with_app() -> Store:
    s = MemoryStore()
    s.create("apps", "a1", {"app_id": "a1"})
    return s


def test_note_idempotency_gives_one_note_and_one_event() -> None:
    s = store_with_app()
    first, created = create_note(s, "a1", "o@x.com", "Owner confirmed scope.", "key-1", NOW)
    again, created_again = create_note(s, "a1", "o@x.com", "Owner confirmed scope.", "key-1", NOW)
    assert created and not created_again and first == again
    assert len(list_notes(s, "a1")) == 1
    assert [e["kind"] for e in s.list("apps/a1/events")] == ["note_added"]


def test_note_limits_edit_window_and_soft_delete() -> None:
    s = store_with_app()
    with pytest.raises(RegistryError):
        create_note(s, "a1", "o@x.com", "x" * 5001, "k", NOW)
    note, _ = create_note(s, "a1", "o@x.com", "draft", "k2", NOW)
    with pytest.raises(ForbiddenError):
        edit_note(s, note["note_id"], "someone@x.com", "hijack", NOW)
    edited = edit_note(s, note["note_id"], "o@x.com", "final", NOW + timedelta(minutes=5))
    assert edited["text"] == "final" and edited["history"][0]["text"] == "draft"
    with pytest.raises(ForbiddenError):
        edit_note(s, note["note_id"], "o@x.com", "late", NOW + timedelta(minutes=16))
    with pytest.raises(RegistryError):
        delete_note(s, note["note_id"], "o@x.com", "app_owner", "  ", NOW)
    delete_note(s, note["note_id"], "o@x.com", "app_owner", "duplicate", NOW)
    assert list_notes(s, "a1") == []
    assert s.get("notes", note["note_id"])["delete_reason"] == "duplicate"  # type: ignore[index]


def test_import_example_creates_intake_apps() -> None:
    s = MemoryStore()
    report = import_csv(
        s,
        ROOT / "imports/example_export.csv",
        ROOT / "imports/example_mapping.yaml",
        "admin@x.com",
        NOW,
    )
    assert report.errors == [] and len(report.created) == 2
    app = s.get("apps", "branch-queue-forecaster")
    assert app is not None and app["stage"] == "intake" and app["platform"] == "abacus"
    assert app["usage_provenance"] == "ASSUMPTION" and app["provenance"] == "IMPORTED"
    assert s.get("apps", "supplier-email-triage")["platform"] == "copilot"  # type: ignore[index]


def test_import_is_all_or_nothing(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Application Name,Owner Email,Department,Platform,Risk Rating,"
        "Problem Statement,Monthly Spend,Monthly Budget,Active Users\n"
        "Too Short,a@x.com,Ops,Abacus,Low,Too short a problem,1,2,3\n"
    )
    s = MemoryStore()
    report = import_csv(s, bad, ROOT / "imports/example_mapping.yaml", "admin@x.com", NOW)
    assert report.errors and s.list("apps") == []


@pytest.mark.parametrize("value", ["=SUM(1+1)", "+1", "-2", "@cmd", "\tx"])
def test_csv_cells_neutralize_formulas(value: str) -> None:
    assert safe_cell(value).startswith("'")
    assert safe_cell("normal text") == "normal text"
