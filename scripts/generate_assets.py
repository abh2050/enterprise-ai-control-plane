"""Generate the atmosphere images in configs/visual_assets.yaml with the Higgsfield API.

    uv run python scripts/generate_assets.py [asset_id ...] [--dry-run]

The key comes from HIGGSFIELD_API_KEY or HF_CREDENTIALS ("key-id:key-secret") in the
environment or .env, and is never printed. Each take is saved to assets/generated/<id>-<n>.png
and logged in assets/generated/manifest.json (prompt, model, request id, date). Existing
takes are skipped, so a rerun never pays twice. Cost: about 0.0032 USD per Soul V2 image.
"""

import json
import os
import socket
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "visual_assets.yaml"
OUT = ROOT / "assets" / "generated"
MANIFEST = OUT / "manifest.json"
API = "https://api.higgsfield.ai"

# This network has no working IPv6 route; resolve IPv4 only.
_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [x for x in _getaddrinfo(*a, **k) if x[0] == socket.AF_INET]


def credentials() -> str:
    for name in ("HIGGSFIELD_API_KEY", "HF_CREDENTIALS"):
        if os.environ.get(name):
            return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() in ("HIGGSFIELD_API_KEY", "HF_CREDENTIALS") and value.strip():
                return value.strip().strip("'\"")
    raise SystemExit("Set HIGGSFIELD_API_KEY or HF_CREDENTIALS (key-id:key-secret)")


def call(url: str, key: str, body: dict[str, object] | None = None) -> dict[str, object]:
    headers = {"Authorization": f"Key {key}", "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    method = "POST" if data else "GET"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310
    with urllib.request.urlopen(req, timeout=60) as res:  # noqa: S310 (fixed https host)
        result: dict[str, object] = json.load(res)
    return result


def generate(key: str, model: str, prompt: str, ratio: str, resolution: str) -> tuple[str, str]:
    body = {"prompt": prompt, "aspect_ratio": ratio, "resolution": resolution}
    job = call(f"{API}/{model}", key, body)
    status_url = str(job["status_url"])
    for _ in range(120):
        time.sleep(4)
        state = call(status_url, key)
        if state.get("status") == "completed":
            images = state.get("images") or []
            return str(job["request_id"]), str(images[0]["url"])  # type: ignore[index]
        if state.get("status") not in ("queued", "in_progress"):
            raise RuntimeError(f"generation {job['request_id']} ended as {state.get('status')}")
    raise TimeoutError(f"generation {job['request_id']} did not finish")


def main(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    wanted = {a for a in argv if not a.startswith("--")}
    cfg = yaml.safe_load(CONFIG.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    done = {m["file"] for m in manifest}
    plan = [
        (a, n)
        for a in cfg["assets"]
        if not wanted or a["id"] in wanted
        for n in range(1, int(a.get("takes", 1)) + 1)
        if f"{a['id']}-{n}.png" not in done
    ]
    print(f"{len(plan)} images to generate, about {len(plan) * 0.0032:.3f} USD", file=sys.stderr)
    if dry or not plan:
        return
    key = credentials()
    for asset, n in plan:
        prompt = f"{asset['prompt'].strip()}, {cfg['style_suffix'].strip()}"
        request_id, url = generate(
            key, cfg["model"], prompt, cfg["aspect_ratio"], cfg["resolution"]
        )
        name = f"{asset['id']}-{n}.png"
        with urllib.request.urlopen(url, timeout=120) as res:  # noqa: S310 (Higgsfield CDN URL)
            (OUT / name).write_bytes(res.read())
        manifest.append(
            {
                "file": name,
                "asset": asset["id"],
                "use": asset["use"],
                "model": cfg["model"],
                "prompt": prompt,
                "aspect_ratio": cfg["aspect_ratio"],
                "resolution": cfg["resolution"],
                "request_id": request_id,
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
        MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
        print(f"saved {name}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
