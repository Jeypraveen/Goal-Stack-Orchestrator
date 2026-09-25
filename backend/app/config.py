"""
Application configuration via pydantic-settings.
Reads from environment variables (or .env file in development).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the Jps.ai backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Database connection ---
    database_url: str = "sqlite:///orchestrator.db"

    # --- Groq (Router LLM) ---
    groq_api_key: str = ""

    # --- Google AI Studio (Gemini Flash - Agent LLM) ---
    google_api_key: str = ""
    agent_llm_model: str = "gemini-3.6-flash"

    # --- App ---
    environment: str = "development"

    # --- Derived settings ---
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def validate_required(self) -> None:
        """Validate that all required settings are present. Call at app startup."""
        missing = []
        for field in ["groq_api_key", "google_api_key"]:
            if not getattr(self, field):
                missing.append(field.upper())
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in your API keys."
            )


@lru_cache
def get_settings() -> Settings:
    """Get the cached Settings instance."""
    return Settings()


# Convenience alias - import this everywhere
settings = get_settings()
