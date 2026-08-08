import os
import sys
import pytest

# Ensure the root directory is on the path so we can import src and api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """
    Automatically mock and reset environment config for every test run
    to isolate tests from real local environment variables.
    """
    # Set mock environment variables
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("API_KEY", "")

    # Apply configuration overrides directly to the config singleton
    from src.config import config
    config.GROQ_API_KEY = "test-groq-key"
    config.GEMINI_API_KEY = "test-gemini-key"
    config.TAVILY_API_KEY = "test-tavily-key"
    config.API_KEY = ""
    config.MAX_RETRIES = 1
    config.LOG_LEVEL = "DEBUG"
