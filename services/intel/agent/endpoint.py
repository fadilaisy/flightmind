"""Glue between /api/ask and the agent (SCRUM-36).

The agent is on only when ANTHROPIC_API_KEY itself is set and non-empty. No other credential
the SDK could find (for example ANTHROPIC_AUTH_TOKEN) switches it on, and the key is passed to
the SDK explicitly so the SDK does not look at the environment for another credential.
The key is never logged and never put in a response.
"""
import asyncio
import importlib.util
import logging
import os
from typing import Any, Optional

from agent.agent import CALL_TIMEOUT_SECONDS, run_agent
from agent.api_client import ApiClient
from agent.evidence import not_enough

log = logging.getLogger("flightmind.agent")

_warned_missing_sdk = False


def agent_enabled() -> bool:
    """True when ANTHROPIC_API_KEY is non-empty, FLIGHTMIND_ASK is not 'canned' and the SDK imports."""
    global _warned_missing_sdk
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return False
    if os.environ.get("FLIGHTMIND_ASK", "").strip().lower() == "canned":
        return False
    if importlib.util.find_spec("anthropic") is None:
        if not _warned_missing_sdk:
            _warned_missing_sdk = True
            log.error("ANTHROPIC_API_KEY is set but the anthropic package is not installed; using canned answers")
        return False
    return True


def make_client() -> Any:
    """Build the real Claude client from ANTHROPIC_API_KEY only."""
    import anthropic

    return anthropic.AsyncAnthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"].strip(),
        timeout=CALL_TIMEOUT_SECONDS,
        max_retries=1,
    )


def _claude_failure(name: str) -> dict:
    response = not_enough([{"tool": "claude_api", "error": name}])
    return response


async def answer_question(question: str, api_app: Any, *, client: Optional[Any] = None, clock: Optional[Any] = None) -> dict:
    """Run the agent on the in-process API app. Claude API errors become not_enough_evidence."""
    import anthropic
    import httpx

    api = ApiClient(app=api_app)
    if client is None:
        client = make_client()
    kwargs = {} if clock is None else {"clock": clock}
    try:
        return await run_agent(client, api, question, **kwargs)
    except anthropic.AuthenticationError:
        log.error("Claude API call failed: AuthenticationError (check ANTHROPIC_API_KEY)")
        return _claude_failure("AuthenticationError")
    except anthropic.RateLimitError:
        log.error("Claude API call failed: RateLimitError")
        return _claude_failure("RateLimitError")
    except anthropic.APITimeoutError:
        log.error("Claude API call failed: APITimeoutError")
        return _claude_failure("APITimeoutError")
    except anthropic.APIConnectionError:
        log.error("Claude API call failed: APIConnectionError")
        return _claude_failure("APIConnectionError")
    except anthropic.APIStatusError as exc:
        log.error("Claude API call failed: %s (HTTP %s)", type(exc).__name__, getattr(exc, "status_code", "?"))
        return _claude_failure(type(exc).__name__)
    except (anthropic.AnthropicError, asyncio.TimeoutError, httpx.HTTPError) as exc:
        log.error("Claude API call failed: %s", type(exc).__name__)
        return _claude_failure(type(exc).__name__)
