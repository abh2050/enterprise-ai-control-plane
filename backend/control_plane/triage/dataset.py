"""Banking77 import, verification, and deterministic splits (Section 6.1).

Source: PolyAI-LDN/task-specific-datasets, license CC BY 4.0.
Casanueva, Temčinas, Gerz, Henderson, Vulić. "Efficient Intent Detection with Dual
Sentence Encoders." Proceedings of the 2nd Workshop on NLP for ConvAI, 2020.

Raw text stays in data/raw/ (gitignored). Split files in data/splits/ hold row ids only,
so the committed repository never contains evaluation text.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SPLITS_DIR = DATA_DIR / "splits"
MANIFEST_PATH = DATA_DIR / "manifest.json"

SOURCE_REPO = "https://github.com/PolyAI-LDN/task-specific-datasets"
RAW_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{commit}/banking_data/{name}"
FILES = ("train.csv", "test.csv", "categories.json")
EXPECTED_HEADERS = ["text", "category"]
EXPECTED_LABELS = 77

SEED = 42
DEV_PER_LABEL = 10
FROZEN_PER_LABEL = 20
SHADOW_DAYS = 14

SENSITIVE_INTENTS = (
    "compromised_card",
    "lost_or_stolen_card",
    "lost_or_stolen_phone",
    "card_payment_not_recognised",
    "cash_withdrawal_not_recognised",
    "direct_debit_payment_not_recognised",
)
OUT_OF_SCOPE = "out_of_scope"


class DatasetError(RuntimeError):
    pass


@dataclass(frozen=True)
class Case:
    case_id: str
    text: str
    label: str


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_ids(ids: list[str]) -> str:
    return sha256_bytes("\n".join(ids).encode())


def load_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text())
    return manifest


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# Fetch and verify


def fetch(raw_dir: Path = RAW_DIR) -> list[str]:
    """Download the pinned files and fail on any hash, header, or label mismatch."""
    manifest = load_manifest()
    commit = manifest["source_commit"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for entry in manifest["files"]:
        url = RAW_URL.format(commit=commit, name=entry["name"])
        if not url.startswith("https://"):
            raise DatasetError(f"refusing non-https url {url}")
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (https checked)
            data = resp.read()
        digest = sha256_bytes(data)
        if digest != entry["sha256"]:
            raise DatasetError(f"{entry['name']}: sha256 {digest} != pinned {entry['sha256']}")
        (raw_dir / entry["name"]).write_bytes(data)
        report.append(f"{entry['name']}: {len(data)} bytes, sha256 verified")
    verify(raw_dir)
    return report


def verify(raw_dir: Path = RAW_DIR) -> None:
    manifest = load_manifest()
    for entry in manifest["files"]:
        path = raw_dir / entry["name"]
        if not path.exists():
            raise DatasetError(f"{path} missing; run `cp data fetch`")
        if sha256_bytes(path.read_bytes()) != entry["sha256"]:
            raise DatasetError(f"{entry['name']}: hash differs from manifest")
    categories = load_categories(raw_dir)
    if len(categories) != EXPECTED_LABELS:
        raise DatasetError(f"expected {EXPECTED_LABELS} labels, found {len(categories)}")
    for name in ("train.csv", "test.csv"):
        with (raw_dir / name).open(newline="") as fh:
            header = next(csv.reader(fh))
        if header != EXPECTED_HEADERS:
            raise DatasetError(f"{name}: headers {header} != {EXPECTED_HEADERS}")
        labels = {row.label for row in _read_rows(raw_dir, name)}
        if labels != set(categories):
            raise DatasetError(f"{name}: label set differs from categories.json")
    validate_sensitive(categories)


def validate_sensitive(categories: list[str]) -> None:
    missing = [s for s in SENSITIVE_INTENTS if s not in categories]
    if missing:
        raise DatasetError(f"sensitive intents not in categories.json: {missing}")


def load_categories(raw_dir: Path = RAW_DIR) -> list[str]:
    cats: list[str] = json.loads((raw_dir / "categories.json").read_text())
    return cats


def _read_rows(raw_dir: Path, name: str) -> list[Case]:
    prefix = name.removesuffix(".csv")
    with (raw_dir / name).open(newline="") as fh:
        return [
            Case(case_id=f"{prefix}:{i}", text=row["text"], label=row["category"])
            for i, row in enumerate(csv.DictReader(fh))
        ]


# Splits


def _per_label(rows: list[Case]) -> dict[str, list[Case]]:
    groups: dict[str, list[Case]] = defaultdict(list)
    for row in rows:
        groups[row.label].append(row)
    return groups


def make_splits(raw_dir: Path = RAW_DIR) -> dict[str, Any]:
    """Create the four splits with seed 42 and write id-only split files."""
    verify(raw_dir)
    categories = load_categories(raw_dir)
    train = _read_rows(raw_dir, "train.csv")
    test = _read_rows(raw_dir, "test.csv")

    # Train rows whose text also appears in test would leak evaluation text into prompts
    # (development examples) and into classifier training. Drop them.
    test_texts = {normalize(r.text) for r in test}
    overlap = [r.case_id for r in train if normalize(r.text) in test_texts]
    train = [r for r in train if normalize(r.text) not in test_texts]

    rng = np.random.default_rng(SEED)
    dev: list[str] = []
    clf_train: list[str] = []
    frozen: list[str] = []
    shadow: list[str] = []
    train_groups = _per_label(train)
    test_groups = _per_label(test)
    for label in categories:  # categories.json order keeps this deterministic
        t = train_groups[label]
        order = rng.permutation(len(t))
        dev += [t[i].case_id for i in order[:DEV_PER_LABEL]]
        clf_train += [t[i].case_id for i in order[DEV_PER_LABEL:]]
        s = test_groups[label]
        order = rng.permutation(len(s))
        if len(s) < FROZEN_PER_LABEL:
            raise DatasetError(f"{label}: only {len(s)} test rows")
        frozen += [s[i].case_id for i in order[:FROZEN_PER_LABEL]]
        shadow += [s[i].case_id for i in order[FROZEN_PER_LABEL:]]

    shadow = [shadow[i] for i in rng.permutation(len(shadow))]
    days = [d.tolist() for d in np.array_split(np.array(shadow, dtype=object), SHADOW_DAYS)]

    splits: dict[str, list[str]] = {
        "dev": dev,
        "classifier_train": clf_train,
        "frozen_eval": frozen,
        "shadow_pool": shadow,
    }
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    for name, ids in splits.items():
        body: dict[str, Any] = {"split": name, "seed": SEED, "row_count": len(ids), "ids": ids}
        if name == "shadow_pool":
            body["days"] = days
        _write_json(SPLITS_DIR / f"{name}.json", body)
        summary[name] = {"row_count": len(ids), "sha256": sha256_ids(ids), "seed": SEED}

    manifest = load_manifest()
    manifest["dedup"] = {
        "rule": "drop train rows whose normalized text appears in test.csv",
        "train_rows_dropped": overlap,
    }
    manifest["splits"] = summary
    _write_json(MANIFEST_PATH, manifest)
    return summary


def load_split(name: str, raw_dir: Path = RAW_DIR) -> list[Case]:
    body = json.loads((SPLITS_DIR / f"{name}.json").read_text())
    ids: list[str] = body["ids"]
    expected = load_manifest()["splits"][name]["sha256"]
    if sha256_ids(ids) != expected:
        raise DatasetError(f"split {name} does not match manifest hash")
    by_id = {r.case_id: r for f in ("train.csv", "test.csv") for r in _read_rows(raw_dir, f)}
    return [by_id[i] for i in ids]


def shadow_days() -> list[list[str]]:
    days: list[list[str]] = json.loads((SPLITS_DIR / "shadow_pool.json").read_text())["days"]
    return days


def dataset_records() -> list[dict[str, Any]]:
    """Rows for the ``datasets`` collection."""
    manifest = load_manifest()
    files = {f["name"]: f["sha256"] for f in manifest["files"]}
    source = {"dev": "train.csv", "classifier_train": "train.csv"}
    return [
        {
            "dataset_id": f"banking77_{name}",
            "source_url": SOURCE_REPO,
            "source_commit": manifest["source_commit"],
            "sha256": files[source.get(name, "test.csv")],
            "split": name,
            "row_count": info["row_count"],
            "seed": info["seed"],
        }
        for name, info in manifest["splits"].items()
    ]
