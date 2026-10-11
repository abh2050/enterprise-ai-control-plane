"""LLM triage configs: prompts, structured output, and the response cache (Section 6.2).

A prompt holds the label catalog, development-set examples, and the one case being
triaged. Frozen evaluation rows never appear as examples; ``build_static_prompt``
refuses any example whose text matches a frozen evaluation row.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from control_plane.triage.dataset import OUT_OF_SCOPE, REPO_ROOT, Case, normalize

CACHE_DIR = REPO_ROOT / ".cache" / "llm"

INSTRUCTIONS = """You route banking customer support messages to an internal intent label.
Choose exactly one intent from the catalog. If the message is not a banking support
request covered by the catalog, choose "out_of_scope". Give a rationale of at most 300
characters. You only recommend an internal route; you never take action on an account."""


class LeakageError(ValueError):
    pass


def pick_examples(dev: Sequence[Case], per_label: int) -> list[Case]:
    """First ``per_label`` development rows per label, in split order (seeded)."""
    taken: dict[str, int] = {}
    chosen = []
    for case in dev:
        if taken.get(case.label, 0) < per_label:
            chosen.append(case)
            taken[case.label] = taken.get(case.label, 0) + 1
    return chosen


def build_static_prompt(
    categories: Sequence[str],
    examples: Sequence[Case],
    forbidden_texts: Iterable[str],
) -> str:
    forbidden = {normalize(t) for t in forbidden_texts}
    leaked = [e.case_id for e in examples if normalize(e.text) in forbidden]
    if leaked:
        raise LeakageError(f"examples match frozen evaluation rows: {leaked}")
    catalog = "\n".join(f"- {c}" for c in [*categories, OUT_OF_SCOPE])
    shots = "\n".join(f'Message: "{e.text}"\nIntent: {e.label}' for e in examples)
    return f"{INSTRUCTIONS}\n\nIntent catalog:\n{catalog}\n\nExamples:\n{shots}\n"


def build_prompt(static_prompt: str, message: str) -> str:
    return f'{static_prompt}\nMessage: "{message}"\nIntent:'


def prompt_sha256(static_prompt: str) -> str:
    return hashlib.sha256(static_prompt.encode()).hexdigest()


# Structured output and parsing

RATIONALE_MAX_CHARS = 300


def response_schema(categories: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": [*categories, OUT_OF_SCOPE]},
            "rationale": {"type": "string", "maxLength": RATIONALE_MAX_CHARS},
        },
        "required": ["intent", "rationale"],
    }


def parse_intent(output: dict[str, Any] | None, categories: Sequence[str]) -> str | None:
    """The intent if the output is valid, else None (routed to review by the caller)."""
    if not output:
        return None
    intent = output.get("intent")
    if intent == OUT_OF_SCOPE or intent in categories:
        return str(intent)
    return None


# Response cache: never pay twice for the same prompt


def cache_key(
    backend: str, model_id: str, prompt: str, schema: dict[str, Any], settings: dict[str, Any]
) -> str:
    blob = json.dumps(
        {"b": backend, "m": model_id, "p": prompt, "s": schema, "g": settings}, sort_keys=True
    )
    return hashlib.sha256(blob.encode()).hexdigest()


class ResponseCache:
    """Completed responses on local disk (gitignored; rationales may echo message text)."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or CACHE_DIR

    def _path(self, key: str) -> Path:
        return self._root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        data: dict[str, Any] = json.loads(path.read_text())
        return data

    def put(self, key: str, record: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record))
        os.replace(tmp, path)


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self._interval = 60.0 / requests_per_minute
        self._last = 0.0

    def wait(self) -> None:
        delay = self._last + self._interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()
