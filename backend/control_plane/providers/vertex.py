"""Vertex AI provider through google-genai. Implemented in M3."""

from typing import Any

from control_plane.contracts import Provenance
from control_plane.providers.base import ProviderResponse, TokenCount


class VertexProvider:
    provenance = Provenance.MEASURED

    def count_tokens(self, model_id: str, prompt: str) -> TokenCount:
        raise NotImplementedError("Vertex provider arrives in M3")

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
    ) -> ProviderResponse:
        raise NotImplementedError("Vertex provider arrives in M3")
