"""Shared test fixtures for the agent tests (SCRUM-36). No test here may call the Claude API."""
import pytest

_AGENT_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "FLIGHTMIND_ASK",
    "FLIGHTMIND_LLM_MODEL",
    "FLIGHTMIND_ASK_PER_MINUTE",
    "FLIGHTMIND_ASK_PER_DAY",
)


@pytest.fixture(autouse=True)
def _clean_agent_env(monkeypatch):
    """Start every test with the agent off, whatever the developer's shell holds."""
    for name in _AGENT_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def anyio_backend():
    return "asyncio"
