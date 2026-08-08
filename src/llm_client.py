"""
llm_client.py — Unified LLM client with Groq-first, Gemini-fallback strategy.

Design decisions:
  - Groq is primary: fast inference, great for structured output.
  - Gemini is the fallback: kicks in if Groq raises ANY exception.
  - Pydantic validation failure triggers a retry (up to MAX_RETRIES).
    After all retries, raises a descriptive RuntimeError so the calling
    step can decide how to handle gracefully.
  - All prompts arrive as (system, user) tuples so the client is reusable
    across all three steps without knowing their internals.

Usage:
    from src.llm_client import call_with_retry
    from src.schemas import FitScoreOutput

    result: FitScoreOutput = call_with_retry(
        system_prompt=FIT_SCORE_SYSTEM,
        user_prompt=fit_score_prompt(...),
        schema=FitScoreOutput,
    )
"""

import json
import time
from typing import Type, TypeVar

import groq
import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Initialise clients (lazy — only used if the key is present) ───────────────

_groq_client: groq.Groq | None = None
_gemini_configured = False


def _get_groq_client() -> groq.Groq:
    global _groq_client
    if _groq_client is None:
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in config/.env")
        _groq_client = groq.Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _configure_gemini() -> None:
    global _gemini_configured
    if not _gemini_configured:
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in config/.env")
        genai.configure(api_key=config.GEMINI_API_KEY)
        _gemini_configured = True


# ── Core LLM call helpers ─────────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Make a single Groq API call and return the raw text response."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        timeout=config.REQUEST_TIMEOUT_S,
    )
    return response.choices[0].message.content or ""


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Make a single Gemini API call and return the raw text response."""
    _configure_gemini()
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=config.TEMPERATURE,
            max_output_tokens=config.MAX_TOKENS,
        ),
    )
    response = model.generate_content(user_prompt)
    return response.text or ""


def _parse_json_response(raw: str) -> dict:
    """
    Strip markdown fences if the LLM accidentally includes them,
    then parse as JSON. Raises json.JSONDecodeError on failure.
    """
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


# ── Public interface ──────────────────────────────────────────────────────────

def call_with_retry(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    max_retries: int | None = None,
) -> T:
    """
    Call the LLM (Groq first, Gemini fallback) and validate the response
    against a Pydantic schema. Retries up to `max_retries` times on
    validation failure before raising RuntimeError.

    Args:
        system_prompt: The system-role message.
        user_prompt:   The user-role message.
        schema:        A Pydantic BaseModel subclass to validate against.
        max_retries:   Override config.MAX_RETRIES for this call.

    Returns:
        A validated instance of `schema`.

    Raises:
        RuntimeError: If all retries are exhausted without a valid response.
    """
    retries = max_retries if max_retries is not None else config.MAX_RETRIES
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        provider = "groq"
        try:
            # ── Attempt Groq ──────────────────────────────────────────────
            t0 = time.perf_counter()
            try:
                raw = _call_groq(system_prompt, user_prompt)
                logger.debug(
                    "Groq call succeeded",
                    extra={"attempt": attempt, "provider": "groq", "raw_length": len(raw)},
                )
            except Exception as groq_err:
                # Groq failed — fall back to Gemini
                provider = "gemini"
                logger.warning(
                    f"Groq call failed (attempt {attempt}), falling back to Gemini",
                    extra={"error": str(groq_err), "attempt": attempt},
                )
                raw = _call_gemini(system_prompt, user_prompt)
                logger.debug(
                    "Gemini fallback succeeded",
                    extra={"attempt": attempt, "provider": "gemini"},
                )

            duration_ms = (time.perf_counter() - t0) * 1000

            # ── Parse and validate ────────────────────────────────────────
            data = _parse_json_response(raw)
            validated = schema.model_validate(data)

            logger.info(
                f"LLM call validated successfully",
                extra={
                    "schema": schema.__name__,
                    "provider": provider,
                    "attempt": attempt,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return validated

        except (json.JSONDecodeError, ValidationError, ValueError) as err:
            last_error = err
            logger.warning(
                f"Validation failed on attempt {attempt}/{retries}: {err}",
                extra={"schema": schema.__name__, "attempt": attempt, "error": str(err)},
            )
            if attempt < retries:
                # Brief back-off before retry
                time.sleep(1.0 * (attempt + 1))
            continue

        except Exception as err:
            # Both Groq and Gemini failed with a non-validation error
            last_error = err
            logger.error(
                f"LLM call failed entirely on attempt {attempt}: {err}",
                extra={"attempt": attempt, "error": str(err)},
            )
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
            continue

    raise RuntimeError(
        f"LLM call for schema '{schema.__name__}' failed after {retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def call_raw(system_prompt: str, user_prompt: str) -> str:
    """
    Simple raw LLM call (no schema validation) used for cheap extraction tasks
    like pulling the company name from a JD. Groq-first, Gemini fallback.
    """
    try:
        return _call_groq(system_prompt, user_prompt).strip()
    except Exception as err:
        logger.warning(f"Groq raw call failed, trying Gemini: {err}")
        return _call_gemini(system_prompt, user_prompt).strip()
