"""Required test 7: no frozen evaluation row appears in any prompt."""

import pytest

from control_plane.triage import dataset as ds
from control_plane.triage.llm import (
    LeakageError,
    build_prompt,
    build_static_prompt,
    pick_examples,
)

needs_data = pytest.mark.skipif(
    not (ds.RAW_DIR / "test.csv").exists(), reason="run `cp data fetch` first"
)


def test_guard_rejects_planted_leak() -> None:
    frozen = [ds.Case("test:1", "Where is my new card?", "card_arrival")]
    planted = [ds.Case("train:9", "  where is my NEW card? ", "card_arrival")]
    with pytest.raises(LeakageError):
        build_static_prompt(["card_arrival"], planted, [c.text for c in frozen])


@needs_data
def test_no_frozen_row_in_any_prompt() -> None:
    categories = ds.load_categories()
    dev = ds.load_split("dev")
    frozen = ds.load_split("frozen_eval")
    frozen_norm = {ds.normalize(c.text) for c in frozen}

    # Examples come from dev only and none of them matches a frozen row.
    examples = pick_examples(dev, per_label=10)
    assert {e.case_id for e in examples} <= {c.case_id for c in dev}
    assert not {ds.normalize(e.text) for e in examples} & frozen_norm

    static = build_static_prompt(categories, examples, [c.text for c in frozen])
    static_norm = ds.normalize(static)
    leaked = [c.case_id for c in frozen if f'"{ds.normalize(c.text)}"' in static_norm]
    assert leaked == []

    # A per-case prompt is the checked static prompt plus only the case being triaged.
    for case in frozen:
        prompt = build_prompt(static, case.text)
        assert prompt.startswith(static)
        assert prompt[len(static) :] == f'\nMessage: "{case.text}"\nIntent:'


@needs_data
def test_splits_are_disjoint_and_dev_has_no_test_text() -> None:
    splits = {
        n: ds.load_split(n) for n in ("dev", "classifier_train", "frozen_eval", "shadow_pool")
    }
    ids = [c.case_id for cases in splits.values() for c in cases]
    assert len(ids) == len(set(ids))
    test_text = {ds.normalize(c.text) for n in ("frozen_eval", "shadow_pool") for c in splits[n]}
    for name in ("dev", "classifier_train"):
        assert not {ds.normalize(c.text) for c in splits[name]} & test_text, name


def test_risk_suite_has_no_banking77_text() -> None:
    if not (ds.RAW_DIR / "test.csv").exists():
        pytest.skip("run `cp data fetch` first")
    from control_plane.triage.evaluate import load_risk_suite

    corpus = {
        ds.normalize(c.text)
        for f in ("train.csv", "test.csv")
        for c in ds._read_rows(ds.RAW_DIR, f)
    }
    assert not [r["case_id"] for r in load_risk_suite() if ds.normalize(r["text"]) in corpus]
