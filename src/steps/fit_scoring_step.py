"""
fit_scoring_step.py — Step 2: Resume vs JD Fit Scoring.

Takes the resume, job description, and company research from state,
asks the LLM to produce a structured FitScoreOutput with:
  - match_score (0-100)
  - matched_skills
  - gap_skills
  - score_reasoning
  - top_selling_points

All output is validated via Pydantic before being stored on state.
"""

import time

from src.llm_client import call_with_retry
from src.logger import get_logger, log_step
from src.prompts import FIT_SCORE_SYSTEM, fit_score_prompt
from src.schemas import AgentState, FitScoreOutput

logger = get_logger(__name__)

STEP_NAME = "fit_scoring"


def execute(state: AgentState) -> AgentState:
    """
    Run the Fit Scoring step.

    Reads:  state.resume_text, state.job_description, state.research
    Writes: state.fit_score

    Args:
        state: The shared AgentState scratchpad (must have research populated).

    Returns:
        Updated AgentState with fit_score populated (or error recorded).
    """
    t0 = time.perf_counter()
    logger.info(f"Starting step: {STEP_NAME}")

    try:
        # Build company context from research output (may be a stub if Step 1 failed)
        research = state.research
        if research:
            company_context = (
                f"Company: {research.company_name}\n"
                f"Overview: {research.company_summary}\n"
                f"Culture signals: {'; '.join(research.culture_signals) or 'None available'}"
            )
        else:
            company_context = "No company research available."

        fit_output: FitScoreOutput = call_with_retry(
            system_prompt=FIT_SCORE_SYSTEM,
            user_prompt=fit_score_prompt(
                resume_text=state.resume_text,
                job_description=state.job_description,
                company_context=company_context,
            ),
            schema=FitScoreOutput,
        )

        state.fit_score = fit_output

        duration_ms = (time.perf_counter() - t0) * 1000
        state.record_step(STEP_NAME, duration_ms, success=True)
        log_step(logger, STEP_NAME, duration_ms, success=True)

        logger.info(
            f"Fit score: {fit_output.match_score}/100",
            extra={
                "score": fit_output.match_score,
                "matched_count": len(fit_output.matched_skills),
                "gap_count": len(fit_output.gap_skills),
            },
        )

    except Exception as err:
        duration_ms = (time.perf_counter() - t0) * 1000
        error_msg = str(err)
        logger.error(f"Fit scoring step failed: {error_msg}")
        state.record_step(STEP_NAME, duration_ms, success=False, error=error_msg)
        log_step(logger, STEP_NAME, duration_ms, success=False, error=error_msg)
        # state.fit_score remains None — cover letter step will handle gracefully

    return state
