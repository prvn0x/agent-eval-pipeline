from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Eval Pipeline"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2"
    llm_cache_ttl_seconds: int = 86400

    self_updater_min_occurrences: int = 3
    annotation_auto_label_threshold: float = 0.7
    sync_eval: bool = False  # skip Celery; run evaluation inline (used on Render)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        return (
            self.database_url
            .replace("postgresql://", "postgresql+asyncpg://")
            .replace("postgres://", "postgresql+asyncpg://")
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ollama_base_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
