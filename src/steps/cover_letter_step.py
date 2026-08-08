"""
cover_letter_step.py — Step 3: Tailored Cover Letter Generation.

Uses the structured outputs of Steps 1 & 2 to write a targeted cover
letter. The letter acknowledges gaps honestly rather than ignoring them,
which makes it more credible and shows self-awareness.

If FitScoreOutput is missing (Step 2 failed), falls back to generating
a letter based only on the JD and resume — still useful, just less targeted.
"""

import time

from src.llm_client import call_with_retry
from src.logger import get_logger, log_step
from src.prompts import COVER_LETTER_SYSTEM, cover_letter_prompt
from src.schemas import AgentState, CoverLetterOutput

logger = get_logger(__name__)

STEP_NAME = "cover_letter"


def execute(state: AgentState) -> AgentState:
    """
    Run the Cover Letter step.

    Reads:  state.research, state.fit_score, state.resume_text, state.job_description
    Writes: state.cover_letter

    Args:
        state: The shared AgentState scratchpad.

    Returns:
        Updated AgentState with cover_letter populated (or error recorded).
    """
    t0 = time.perf_counter()
    logger.info(f"Starting step: {STEP_NAME}")

    try:
        # ── Pull context from previous steps ─────────────────────────────
        research = state.research
        fit = state.fit_score

        company_name = research.company_name if research else "the company"
        company_summary = research.company_summary if research else ""
        culture_signals = research.culture_signals if research else []

        top_selling_points = fit.top_selling_points if fit else []
        gap_skills = fit.gap_skills if fit else []

        if not fit:
            logger.warning(
                "FitScoreOutput not available — writing cover letter without gap analysis",
                extra={"step": STEP_NAME},
            )

        # ── LLM call → CoverLetterOutput ──────────────────────────────────
        cover_output: CoverLetterOutput = call_with_retry(
            system_prompt=COVER_LETTER_SYSTEM,
            user_prompt=cover_letter_prompt(
                resume_text=state.resume_text,
                job_description=state.job_description,
                company_name=company_name,
                company_summary=company_summary,
                culture_signals=culture_signals,
                top_selling_points=top_selling_points,
                gap_skills=gap_skills,
            ),
            schema=CoverLetterOutput,
        )

        state.cover_letter = cover_output

        duration_ms = (time.perf_counter() - t0) * 1000
        state.record_step(STEP_NAME, duration_ms, success=True)
        log_step(logger, STEP_NAME, duration_ms, success=True)

    except Exception as err:
        duration_ms = (time.perf_counter() - t0) * 1000
        error_msg = str(err)
        logger.error(f"Cover letter step failed: {error_msg}")
        state.record_step(STEP_NAME, duration_ms, success=False, error=error_msg)
        log_step(logger, STEP_NAME, duration_ms, success=False, error=error_msg)

    return state
