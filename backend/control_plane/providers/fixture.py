"""Deterministic offline provider. Every output is labeled FIXTURE.

The same (model_id, prompt) pair always produces the same answer, token counts, and
latency, so tests and demos are reproducible without credentials.
"""

import hashlib
from typing import Any

from control_plane.contracts import Provenance
from control_plane.providers.base import ProviderResponse, TokenCount


def _digest(*parts: str) -> int:
    joined = "\x1f".join(parts).encode()
    return int.from_bytes(hashlib.sha256(joined).digest()[:8], "big")


class FixtureProvider:
    provenance = Provenance.FIXTURE

    def count_tokens(self, model_id: str, prompt: str) -> TokenCount:
        # Rough 4 characters per token, which is enough for reservation tests.
        return TokenCount(input_tokens=max(1, len(prompt) // 4))

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
    ) -> ProviderResponse:
        h = _digest(model_id, prompt)
        intent_enum: list[str] = (
            response_schema.get("properties", {}).get("intent", {}).get("enum", [])
        )
        intent = intent_enum[h % len(intent_enum)] if intent_enum else "out_of_scope"
        return ProviderResponse(
            output={"intent": intent, "rationale": "Fixture provider output."},
            input_tokens=self.count_tokens(model_id, prompt).input_tokens,
            output_tokens=min(max_output_tokens, 24 + h % 40),
            latency_ms=200 + h % 1_800,
            model_id=model_id,
            provenance=Provenance.FIXTURE,
        )
