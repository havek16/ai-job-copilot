"""
research_step.py — Step 1: Company Research.

Pipeline:
  1. Extract company name from JD (cheap LLM call)
  2. Run web search (may gracefully return nothing)
  3. LLM call → ResearchOutput (validated, with retry)
  4. Log step timing

The step's output is stored on AgentState.research and is available
to all subsequent steps.
"""

import time

from src.llm_client import call_with_retry, call_raw
from src.logger import get_logger, log_step
from src.prompts import (
    EXTRACT_COMPANY_SYSTEM,
    RESEARCH_SYSTEM,
    extract_company_prompt,
    research_prompt,
)
from src.schemas import AgentState, ResearchOutput
from src.tools.web_search import format_search_results, search_company

logger = get_logger(__name__)

STEP_NAME = "research"


def execute(state: AgentState) -> AgentState:
    """
    Run the Research step.

    Mutates state.research with a ResearchOutput.
    On any failure, sets a descriptive error on state and returns
    so the pipeline can continue.

    Args:
        state: The shared AgentState scratchpad.

    Returns:
        Updated AgentState with research populated (or error recorded).
    """
    t0 = time.perf_counter()
    logger.info(f"Starting step: {STEP_NAME}")

    try:
        # ── 1. Extract company name ───────────────────────────────────────
        company_name = call_raw(
            system_prompt=EXTRACT_COMPANY_SYSTEM,
            user_prompt=extract_company_prompt(state.job_description),
        )
        # Sanitise — remove quotes, trailing punctuation
        company_name = company_name.strip('"\'').rstrip(".,;").strip()
        if not company_name or len(company_name) > 100:
            company_name = "the company"

        logger.info(f"Extracted company name: '{company_name}'")

        # ── 2. Web search ────────────────────────────────────────────────
        search_results = search_company(company_name)
        search_snippets = format_search_results(search_results)
        research_skipped = len(search_results) == 0

        if research_skipped:
            logger.warning(
                "Web search returned no results — proceeding with JD-only context",
                extra={"company": company_name},
            )

        # ── 3. LLM → ResearchOutput ───────────────────────────────────────
        research_output: ResearchOutput = call_with_retry(
            system_prompt=RESEARCH_SYSTEM,
            user_prompt=research_prompt(state.job_description, search_snippets),
            schema=ResearchOutput,
        )
        # Carry through the skip flag from actual search result
        research_output.research_skipped = research_skipped

        state.research = research_output

        duration_ms = (time.perf_counter() - t0) * 1000
        state.record_step(STEP_NAME, duration_ms, success=True)
        log_step(logger, STEP_NAME, duration_ms, success=True)

    except Exception as err:
        duration_ms = (time.perf_counter() - t0) * 1000
        error_msg = str(err)
        logger.error(f"Research step failed: {error_msg}")

        # Provide a minimal stub so downstream steps don't crash on None
        state.research = ResearchOutput(
            company_name="Unknown (research step failed)",
            company_summary="Research was unavailable for this run.",
            research_skipped=True,
        )
        state.record_step(STEP_NAME, duration_ms, success=False, error=error_msg)
        log_step(logger, STEP_NAME, duration_ms, success=False, error=error_msg)

    return state
