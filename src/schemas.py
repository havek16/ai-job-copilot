"""
schemas.py — Pydantic models for all structured data in the pipeline.

Every piece of data that crosses a step boundary or comes from an LLM
call is validated here. This ensures the agent never silently passes
garbage downstream.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Company Research
# ─────────────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    """A single web search result snippet."""
    title: str
    url: str
    content: str


class ResearchOutput(BaseModel):
    """Structured output from the Research step."""
    company_name: str = Field(description="Name of the hiring company")
    company_summary: str = Field(
        description="2-3 sentence overview of what the company does"
    )
    recent_news: list[str] = Field(
        default_factory=list,
        description="Up to 3 recent news items or notable facts about the company",
    )
    culture_signals: list[str] = Field(
        default_factory=list,
        description="Signals about engineering culture, tech stack, or values",
    )
    research_skipped: bool = Field(
        default=False,
        description="True if web search was unavailable; summary is LLM-only",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Fit Scoring
# ─────────────────────────────────────────────────────────────────────────────

class FitScoreOutput(BaseModel):
    """Structured output from the Fit Scoring step."""
    match_score: int = Field(
        ge=0,
        le=100,
        description="Overall fit score from 0 (no match) to 100 (perfect match)",
    )
    matched_skills: list[str] = Field(
        description="Skills/experience from the resume that match the JD requirements"
    )
    gap_skills: list[str] = Field(
        description="Skills or experience required by the JD but missing from the resume"
    )
    score_reasoning: str = Field(
        description="2-3 sentence explanation of why this score was assigned"
    )
    top_selling_points: list[str] = Field(
        description="The 3 strongest selling points from the resume for this specific role"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Cover Letter
# ─────────────────────────────────────────────────────────────────────────────

class CoverLetterOutput(BaseModel):
    """Structured output from the Cover Letter step."""
    subject_line: str = Field(
        description="Email subject line for the application"
    )
    cover_letter_body: str = Field(
        description="Full cover letter text, ready to send"
    )
    key_selling_points_used: list[str] = Field(
        description="The selling points woven into the letter"
    )
    gaps_addressed: list[str] = Field(
        default_factory=list,
        description="Gap skills the letter proactively acknowledges or frames positively",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent State — the scratchpad that threads through all steps
# ─────────────────────────────────────────────────────────────────────────────

class StepTiming(BaseModel):
    """Performance metadata for a single step."""
    step_name: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


class AgentState(BaseModel):
    """
    The shared scratchpad that is created at the start of a run and
    passed through each step, accumulating outputs as it goes.
    """
    # ── Inputs ──────────────────────────────────────────────────────────
    resume_text: str = ""
    job_description: str = ""

    # ── Step outputs (populated as the pipeline runs) ────────────────────
    research: Optional[ResearchOutput] = None
    fit_score: Optional[FitScoreOutput] = None
    cover_letter: Optional[CoverLetterOutput] = None

    # ── Metadata ─────────────────────────────────────────────────────────
    step_timings: list[StepTiming] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def record_step(self, name: str, duration_ms: float, success: bool, error: str = "") -> None:
        """Convenience method to append step timing info."""
        self.step_timings.append(
            StepTiming(
                step_name=name,
                duration_ms=round(duration_ms, 2),
                success=success,
                error_message=error or None,
            )
        )
        if error:
            self.errors.append(f"[{name}] {error}")


# ─────────────────────────────────────────────────────────────────────────────
# Final API response
# ─────────────────────────────────────────────────────────────────────────────

class AgentResult(BaseModel):
    """
    The serialised result returned by the FastAPI endpoint.
    Includes all step outputs plus pipeline metadata.
    """
    success: bool
    research: Optional[ResearchOutput] = None
    fit_score: Optional[FitScoreOutput] = None
    cover_letter: Optional[CoverLetterOutput] = None
    step_timings: list[StepTiming] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    total_duration_ms: float = 0.0
