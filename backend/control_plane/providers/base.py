"""Provider contract shared by the fixture and Vertex providers.

Providers never retry. The caller owns retries, deadlines, and budget settlement.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from control_plane.contracts import Provenance


@dataclass(frozen=True)
class TokenCount:
    input_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    output: dict[str, Any]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_id: str
    provenance: Provenance


class ProviderTimeoutError(Exception):
    """The deadline passed after the request was sent; the outcome is unknown."""


class Provider(Protocol):
    provenance: Provenance

    def count_tokens(self, model_id: str, prompt: str) -> TokenCount: ...

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
    ) -> ProviderResponse: ...
