from src.config import Settings


def test_settings_load_defaults():
    """Verify that configuration settings load with expected defaults."""
    settings = Settings()
    assert settings.TEMPERATURE == 0.3
    assert settings.MAX_TOKENS == 2048
    assert settings.API_PORT == 8000
    assert isinstance(settings.MAX_RETRIES, int)


def test_settings_custom_values():
    """Verify that configuration settings can be correctly overridden."""
    settings = Settings(
        GROQ_MODEL="llama-4-test",
        GEMINI_MODEL="gemini-3.0-test",
        TEMPERATURE=0.7,
        API_KEY="prod-key-123",
    )
    assert settings.GROQ_MODEL == "llama-4-test"
    assert settings.GEMINI_MODEL == "gemini-3.0-test"
    assert settings.TEMPERATURE == 0.7
    assert settings.API_KEY == "prod-key-123"
