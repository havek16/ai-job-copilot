"""
agent.py — The AgentLoop: orchestrates the 3-step pipeline.

Design:
  - Each step is a module with an `execute(state) -> state` function.
  - The loop calls steps sequentially, threading the AgentState scratchpad.
  - If a step fails internally, it records the error on state and returns —
    the loop always continues to the next step.
  - Total duration and final AgentResult are assembled here.

This is intentionally visible and simple — no hidden framework magic.
In an interview you can trace the exact execution path in < 1 minute.
"""

import time

from src.logger import get_logger
from src.schemas import AgentResult, AgentState
from src.steps import cover_letter_step, fit_scoring_step, research_step

logger = get_logger(__name__)


class AgentLoop:
    """
    The main agent orchestrator.

    Steps are defined as an ordered list of modules. Each module must expose
    an `execute(state: AgentState) -> AgentState` function.

    Adding a new step is as simple as:
      1. Create a new module in src/steps/
      2. Import it and append it to self.steps
    """

    def __init__(self) -> None:
        # Ordered pipeline — steps run left to right
        self.steps = [
            research_step,
            fit_scoring_step,
            cover_letter_step,
        ]

    def run(self, resume_text: str, job_description: str) -> AgentResult:
        """
        Execute the full pipeline and return a serialisable AgentResult.

        Args:
            resume_text:     Plain text extracted from the resume.
            job_description: Raw JD text pasted by the user.

        Returns:
            AgentResult containing all step outputs and timing metadata.
        """
        run_start = time.perf_counter()

        logger.info(
            "AgentLoop started",
            extra={
                "resume_chars": len(resume_text),
                "jd_chars": len(job_description),
                "step_count": len(self.steps),
            },
        )

        # Initialise the shared scratchpad
        state = AgentState(
            resume_text=resume_text,
            job_description=job_description,
        )

        # ── Execute each step in order ────────────────────────────────────
        for step_module in self.steps:
            step_name = getattr(step_module, "STEP_NAME", step_module.__name__)
            logger.info(f"→ Running step: {step_name}")
            try:
                state = step_module.execute(state)
            except Exception as err:
                # Belt-and-suspenders: step modules should handle their own
                # errors, but we catch here too to protect the loop.
                error_msg = f"Unhandled exception in step '{step_name}': {err}"
                logger.error(error_msg)
                state.errors.append(error_msg)

        total_duration_ms = (time.perf_counter() - run_start) * 1000
        pipeline_success = len(state.errors) == 0 or (
            # Partial success: at least fit score was produced
            state.fit_score is not None
        )

        logger.info(
            "AgentLoop completed",
            extra={
                "total_duration_ms": round(total_duration_ms, 2),
                "success": pipeline_success,
                "error_count": len(state.errors),
                "fit_score": state.fit_score.match_score if state.fit_score else None,
            },
        )

        return AgentResult(
            success=pipeline_success,
            research=state.research,
            fit_score=state.fit_score,
            cover_letter=state.cover_letter,
            step_timings=state.step_timings,
            errors=state.errors,
            total_duration_ms=round(total_duration_ms, 2),
        )
