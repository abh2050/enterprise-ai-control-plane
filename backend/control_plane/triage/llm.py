"""LLM triage prompt construction (Section 6.2). Model calls arrive in M3.

A prompt holds the label catalog, development-set examples, and the one case being
triaged. Frozen evaluation rows never appear as examples; ``build_static_prompt``
refuses any example whose text matches a frozen evaluation row.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence

from control_plane.triage.dataset import OUT_OF_SCOPE, Case, normalize

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
