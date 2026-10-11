import json
from collections import Counter

import pytest

from control_plane.triage import dataset as ds
from control_plane.triage.evaluate import load_risk_suite


def test_manifest_pins_commit_and_hashes() -> None:
    m = ds.load_manifest()
    assert len(m["source_commit"]) == 40
    assert {f["name"] for f in m["files"]} == set(ds.FILES)
    assert all(len(f["sha256"]) == 64 for f in m["files"])
    assert m["license"] == "CC-BY-4.0"


def test_split_sizes_from_committed_split_files() -> None:
    m = ds.load_manifest()["splits"]
    assert m["dev"]["row_count"] == 770
    assert m["frozen_eval"]["row_count"] == 1540
    assert all(s["seed"] == 42 for s in m.values())
    days = ds.shadow_days()
    assert len(days) == 14
    assert sum(len(d) for d in days) == m["shadow_pool"]["row_count"]


def test_sensitive_mismatch_fails() -> None:
    with pytest.raises(ds.DatasetError):
        ds.validate_sensitive(["card_arrival"])


def test_bad_header_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    if not (ds.RAW_DIR / "test.csv").exists():
        pytest.skip("run `cp data fetch` first")
    for f in ds.FILES:
        (tmp_path / f).write_bytes((ds.RAW_DIR / f).read_bytes())
    (tmp_path / "test.csv").write_text("utterance,label\nhello,card_arrival\n")
    with pytest.raises(ds.DatasetError):
        ds.verify(tmp_path)


def test_risk_suite_structure() -> None:
    rows = load_risk_suite()
    assert len(rows) == 60
    assert Counter(r["category"] for r in rows) == {
        "ambiguous": 20,
        "sensitive_indirect": 20,
        "out_of_domain": 20,
    }
    assert len({r["case_id"] for r in rows}) == 60
    meta = json.loads((ds.DATA_DIR / "risk_suite.meta.json").read_text())
    assert meta["provenance"] == "AUTHORED" and meta["rater_count"] == 1
    for r in rows:
        if r["category"] == "sensitive_indirect":
            assert r["expected_route"] == "review" and r["expected_intent"] in ds.SENSITIVE_INTENTS
        if r["category"] == "out_of_domain":
            assert r["expected_route"] == "abstain"
