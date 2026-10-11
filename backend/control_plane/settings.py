"""Runtime settings, read from the environment and an optional .env file."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MICROS_PER_USD = 1_000_000
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class IdentityMode(StrEnum):
    FIXTURE = "fixture"
    IAP = "iap"


class ProviderMode(StrEnum):
    FIXTURE = "fixture"
    VERTEX = "vertex"


class StoreBackend(StrEnum):
    MEMORY = "memory"
    FIRESTORE = "firestore"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    identity_mode: IdentityMode = IdentityMode.FIXTURE
    provider_mode: ProviderMode = ProviderMode.FIXTURE
    store_backend: StoreBackend = StoreBackend.MEMORY
    firestore_emulator_host: str | None = None
    gcp_project: str = "demo-control-plane"

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000

    vertex_location: str = "us-central1"
    vertex_low_cost_model: str = "gemini-3.1-flash-lite"
    vertex_high_capability_model: str = "gemini-3.8-flash"

    iap_audience: str | None = None

    budget_app_daily_usd: int = Field(default=5, ge=0)
    budget_experiment_usd: int = Field(default=40, ge=0)
    budget_experiment_total_usd: int = Field(default=60, ge=0)

    @property
    def budget_app_daily_micros(self) -> int:
        return self.budget_app_daily_usd * MICROS_PER_USD

    @property
    def budget_experiment_micros(self) -> int:
        return self.budget_experiment_usd * MICROS_PER_USD

    @property
    def budget_experiment_total_micros(self) -> int:
        return self.budget_experiment_total_usd * MICROS_PER_USD


class UnsafeBindError(RuntimeError):
    """Fixture identity trusts a request header, so it may only serve localhost."""


def assert_safe_bind(settings: Settings, host: str | None = None) -> None:
    bound = host if host is not None else settings.bind_host
    if settings.identity_mode is IdentityMode.FIXTURE and bound not in LOCAL_HOSTS:
        raise UnsafeBindError(
            f"Fixture identity refuses to bind to {bound!r}. "
            "Bind to 127.0.0.1 or set IDENTITY_MODE=iap."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
