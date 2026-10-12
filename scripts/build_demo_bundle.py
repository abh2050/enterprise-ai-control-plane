"""Package the backend for the in-browser demo (frontend/.demo-data/demo/bundle.zip).

The zip holds the unchanged `control_plane` package plus the committed configs, data, and
evidence it reads. From the Banking77 download (data/raw, gitignored) only the label list
categories.json is included, which gate evaluation needs; the train and test text is
excluded, so the demo shows no case text. Also excluded: the classifier binary (no demo
endpoint loads it) and caches. Entries carry a fixed timestamp so an unchanged tree
produces a byte-identical zip.

    uv run python scripts/build_demo_bundle.py
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / ".demo-data" / "demo"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
# Pure-Python wheels installed in the browser at the uv.lock versions; micropip resolves
# their small dependencies. pydantic, PyYAML and NumPy come prebuilt with Pyodide.
REQUIREMENTS = [
    "fastapi==0.143.0",
    "starlette==1.7.0",
    "pydantic-settings==2.15.0",
    "python-dotenv==1.2.4",
]
PYODIDE_PACKAGES = ["pydantic", "pyyaml", "numpy", "micropip"]


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if "__pycache__" in rel or path.name == ".DS_Store":
        return False
    if rel.startswith("backend/control_plane/"):
        return path.suffix == ".py"
    if rel.startswith("data/"):
        return not rel.startswith("data/raw/") or rel == "data/raw/categories.json"
    if rel.startswith("artifacts/"):
        return not rel.startswith("artifacts/models/")
    return rel.startswith("configs/")


def build() -> dict[str, object]:
    if not (ROOT / "data" / "raw" / "categories.json").exists():
        raise SystemExit("data/raw/categories.json is missing; run `uv run cp data fetch` first")
    files = sorted(
        p
        for top in ("backend/control_plane", "configs", "data", "artifacts")
        for p in (ROOT / top).rglob("*")
        if p.is_file() and included(p)
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "bundle.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            info = zipfile.ZipInfo(p.relative_to(ROOT).as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, p.read_bytes())
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {
        "bundle": "bundle.zip",
        "sha256": digest,
        "files": len(files),
        "bytes": out.stat().st_size,
        "requirements": REQUIREMENTS,
        "pyodide_packages": PYODIDE_PACKAGES,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    m = build()
    print(
        f"{m['files']} files, {m['bytes']:,} bytes, sha256 {str(m['sha256'])[:12]}", file=sys.stderr
    )
