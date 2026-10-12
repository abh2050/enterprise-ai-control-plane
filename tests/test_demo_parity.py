"""The in-browser demo engine must behave exactly like the backend.

The GitHub Pages console runs this same backend in Pyodide (control_plane.browser). This
test replays one scripted session (tests/fixtures/demo_parity.json) against the native
app and against the Pyodide engine under Node, and requires identical statuses and
bodies. Generated ids are normalized. Case text is absent on both sides: the demo bundle
excludes the Banking77 files, and the native run hides them the same way.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from control_plane.api import create_app
from control_plane.settings import Settings
from control_plane.store import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "tests" / "fixtures" / "demo_parity.json"
ENGINE = ROOT / "frontend" / "scripts" / "demo_engine.mjs"
PYODIDE = ROOT / "frontend" / ".demo-data" / "demo" / "pyodide"
HEX32 = re.compile(r"\b[0-9a-f]{32}\b")
RELEASE_SUFFIX = re.compile(r"(\d{8}T\d{6}Z)_[0-9a-f]{4}\b")


def normalize(body: str) -> Any:
    text = RELEASE_SUFFIX.sub(r"\1_<id>", HEX32.sub("<id>", body))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def substitute(body: Any, variables: dict[str, Any]) -> Any:
    """Replace "{name}" values in a request body with captured values."""
    if isinstance(body, dict):
        return {k: substitute(v, variables) for k, v in body.items()}
    if isinstance(body, str) and (m := re.fullmatch(r"\{(\w+)\}", body)):
        return variables[m.group(1)]
    return body


def run_native(scenario: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    def no_raw_text(_: str) -> list[Any]:
        raise FileNotFoundError("Banking77 text is not part of the demo bundle")

    monkeypatch.setattr("control_plane.triage.dataset.load_split", no_raw_text)
    settings = Settings(_env_file=None, fixed_now=scenario["env"]["FIXED_NOW"])
    results: list[dict[str, Any]] = []
    variables: dict[str, Any] = {}
    with TestClient(create_app(settings, MemoryStore()), client=("127.0.0.1", 50000)) as client:
        for step in scenario["steps"]:
            path = re.sub(r"\{(\w+)\}", lambda m: str(variables[m.group(1)]), step["path"])
            headers = {"X-Fixture-User": step["user"]} if step.get("user") else {}
            res = client.request(
                step["method"], path, headers=headers, json=substitute(step.get("body"), variables)
            )
            for name, key in step.get("capture", {}).items():
                value: Any = res.json()
                for part in key.split("."):
                    value = value[part]
                variables[name] = value
            results.append({"name": step["name"], "status": res.status_code, "body": res.text})
    return results


def run_pyodide(tmp_path: Path) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_demo_bundle import build

    build()
    out = tmp_path / "pyodide.json"
    proc = subprocess.run(
        ["node", str(ENGINE), str(SCENARIO), str(out)],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=ROOT / "frontend",
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    results: list[dict[str, Any]] = json.loads(out.read_text())
    return results


@pytest.mark.skipif(
    shutil.which("node") is None or not PYODIDE.exists(),
    reason="needs Node and the vendored runtime (cd frontend && npm run build:demo)",
)
def test_demo_engine_matches_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scenario = json.loads(SCENARIO.read_text())
    native = run_native(scenario, monkeypatch)
    browser = run_pyodide(tmp_path)
    assert [r["name"] for r in browser] == [r["name"] for r in native]
    mismatches = [
        f"{n['name']}: native {n['status']} {n['body'][:200]}"
        f" | demo {b['status']} {b['body'][:200]}"
        for n, b in zip(native, browser, strict=True)
        if n["status"] != b["status"] or normalize(n["body"]) != normalize(b["body"])
    ]
    assert not mismatches, "\n".join(mismatches)


def test_scenario_exercises_rules_not_just_reads() -> None:
    """The session must include rejected writes, or parity would prove little."""
    steps = json.loads(SCENARIO.read_text())["steps"]
    writes = [s for s in steps if s["method"] != "GET"]
    assert len(writes) >= 30
    for name in (
        "illegal move",
        "stale version",
        "submitter cannot approve",
        "activate_full blocked",
    ):
        assert any(s["name"] == name for s in steps)
