"""The public demo bundle carries code, configs and evidence only: no secrets, no case text."""

import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_demo_bundle import build  # noqa: E402

# Shapes of the credentials this project has handled (Google API keys, OAuth client
# secrets, OpenAI and Hugging Face tokens, private keys, service account files).
SECRET = re.compile(
    rb"AIza[0-9A-Za-z_\-]{30,}|GOCSPX-[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}"
    rb"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\"private_key_id\""
)
ALLOWED = ("backend/control_plane/", "configs/", "data/", "artifacts/")


@pytest.fixture(scope="module")
def bundle() -> zipfile.ZipFile:
    if not (ROOT / "data" / "raw" / "categories.json").exists():
        pytest.skip("needs the Banking77 label list (uv run cp data fetch)")
    manifest = build()
    return zipfile.ZipFile(ROOT / "frontend" / ".demo-data" / "demo" / str(manifest["bundle"]))


def test_bundle_holds_only_allowed_paths(bundle: zipfile.ZipFile) -> None:
    names = bundle.namelist()
    assert names, "empty bundle"
    outside = [n for n in names if not n.startswith(ALLOWED)]
    assert outside == []
    assert not [n for n in names if Path(n).name.startswith(".env") or "client_secret" in n]
    assert not [n for n in names if n.startswith("artifacts/models/")]


def test_bundle_has_no_message_text(bundle: zipfile.ZipFile) -> None:
    raw = [n for n in bundle.namelist() if n.startswith("data/raw/")]
    assert raw == ["data/raw/categories.json"]


def test_bundle_has_no_credentials(bundle: zipfile.ZipFile) -> None:
    hits = [n for n in bundle.namelist() if SECRET.search(bundle.read(n))]
    assert hits == []
