"""
config.py — Centralised configuration for AI Job-Application Copilot.

All tunables live here. Values are read from environment variables
(via .env file) with sensible defaults. Never hardcode secrets inline.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API Keys ──────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # ── LLM Settings ─────────────────────────────────────────────────────
    # Groq model — llama-3.3-70b-versatile is fast and capable
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Gemini fallback model
    GEMINI_MODEL: str = "gemini-2.0-flash"
    # Sampling temperature (lower = more deterministic structured output)
    TEMPERATURE: float = 0.3
    # Max tokens per LLM response
    MAX_TOKENS: int = 2048

    # ── Retry / Resilience ───────────────────────────────────────────────
    # Max retries on Pydantic validation failure before giving up a step
    MAX_RETRIES: int = 2
    # HTTP timeout in seconds for web search and LLM API calls
    REQUEST_TIMEOUT_S: int = 20

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # ── FastAPI ──────────────────────────────────────────────────────────
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000


# Singleton config instance used everywhere
config = Settings()
