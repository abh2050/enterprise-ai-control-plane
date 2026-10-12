"""The GCP diagram skill and the diagrams built with it (docs/diagrams/).

1. The icon references are exactly what draw.io ships: re-extracting the pinned
   Sidebar-GCP2.js reproduces references/gcp-icons.json byte for byte.
2. Every committed .drawio passes the skill's validator (exact icon styles, unique ids,
   connected edges, no comments).
3. Every diagram has its exported PNG.
"""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "gcp-architecture-diagram"
sys.path.insert(0, str(SKILL / "scripts"))

import extract_icons  # noqa: E402
import validate_drawio  # noqa: E402

DIAGRAMS = sorted((ROOT / "docs" / "diagrams").glob("[0-9][0-9]_*.drawio"))


def test_icon_references_match_the_pinned_drawio_source() -> None:
    sha, digest = extract_icons.pinned()
    try:
        data = urllib.request.urlopen(extract_icons.URL.format(sha=sha), timeout=20).read()
    except OSError as exc:
        pytest.skip(f"cannot download Sidebar-GCP2.js: {exc}")
    assert hashlib.sha256(data).hexdigest() == digest
    committed = json.loads((SKILL / "references" / "gcp-icons.json").read_text())
    assert extract_icons.extract(data) == committed


def test_diagrams_are_numbered_without_gaps() -> None:
    assert [p.stem[:2] for p in DIAGRAMS] == [f"{i:02d}" for i in range(1, 14)]


@pytest.mark.parametrize("path", DIAGRAMS, ids=lambda p: p.stem)
def test_diagram_is_valid(path: Path) -> None:
    assert validate_drawio.validate(path, validate_drawio.canonical_styles()) == []


@pytest.mark.parametrize("path", DIAGRAMS, ids=lambda p: p.stem)
def test_diagram_has_its_png(path: Path) -> None:
    assert path.with_suffix(".png").exists()
