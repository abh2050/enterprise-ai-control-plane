"""Provider contract shared by the fixture and Google GenAI providers.

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
    output: dict[str, Any] | None  # None when the model returned unparseable JSON
    input_tokens: int
    output_tokens: int  # billed output, including thinking tokens
    latency_ms: int
    model_id: str
    provenance: Provenance
    cached_tokens: int = 0
    thinking_tokens: int = 0
    finish_reason: str | None = None


class ProviderTimeoutError(Exception):
    """The deadline passed after the request was sent; the outcome is unknown."""


class ProviderRejectedError(Exception):
    """The service returned an error response (4xx or 5xx, for example 429).

    Vertex charges only for 200 responses, so the caller releases the reservation.
    """

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"{status}: {message}")
        self.status = status


class Provider(Protocol):
    provenance: Provenance
    backend: str

    def count_tokens(self, model_id: str, prompt: str) -> TokenCount: ...

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
    ) -> ProviderResponse: ...
