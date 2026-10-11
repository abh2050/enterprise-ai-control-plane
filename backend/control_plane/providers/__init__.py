"""Model providers: deterministic fixtures offline, Google GenAI for live runs."""

from control_plane.providers.base import Provider
from control_plane.settings import ProviderMode, Settings


def build_provider(settings: Settings, thinking_level: str = "minimal") -> Provider:
    if settings.provider_mode is ProviderMode.FIXTURE:
        from control_plane.providers.fixture import FixtureProvider

        return FixtureProvider()
    from control_plane.providers.vertex import GenAIProvider

    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
    return GenAIProvider(
        settings.provider_mode.value,
        api_key=key,
        project=settings.gcp_project,
        location=settings.vertex_location,
        thinking_level=thinking_level,
    )
