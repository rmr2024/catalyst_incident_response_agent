from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./incidents.db"
    cors_origins: str = "http://localhost:5173"
    memory_enabled: bool = True
    critical_services: str = "payments,checkout,auth,api-gateway"
    llm_provider: str = "claude"
    llm_model: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    hindsight_url: str = "http://localhost:8888"
    hindsight_api_key: str = ""
    hindsight_bank: str = "incidents"
    novel_threshold: float = 0.25  # similarity threshold below which an incident is flagged as novel

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def critical_list(self) -> list[str]:
        return [s.strip().lower() for s in self.critical_services.split(",") if s.strip()]


settings = Settings()
_memory = {"enabled": settings.memory_enabled}


def memory_enabled() -> bool:
    return _memory["enabled"]


def set_memory_enabled(v: bool) -> None:
    _memory["enabled"] = bool(v)
