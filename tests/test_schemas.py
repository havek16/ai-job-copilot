import pytest
from pydantic import ValidationError
from src.schemas import (
    SearchResult,
    ResearchOutput,
    FitScoreOutput,
    CoverLetterOutput,
    AgentState,
    StepTiming,
)


def test_search_result_validation():
    """Verify that SearchResult validates correct input and requires fields."""
    res = SearchResult(title="Google", url="https://google.com", content="Search engine")
    assert res.title == "Google"
    assert res.url == "https://google.com"
    assert res.content == "Search engine"

    with pytest.raises(ValidationError):
        SearchResult(title="Google")  # missing url & content


def test_research_output_validation():
    """Verify that ResearchOutput validates correct parameters and holds defaults."""
    res = ResearchOutput(
        company_name="Acme Inc.",
        company_summary="Builds anvils and widgets.",
    )
    assert res.company_name == "Acme Inc."
    assert res.recent_news == []
    assert res.culture_signals == []
    assert res.research_skipped is False


def test_fit_score_output_validation():
    """Verify that FitScoreOutput validates correct match scores and enforces range limits."""
    # Valid score
    fit = FitScoreOutput(
        match_score=85,
        matched_skills=["Python", "FastAPI"],
        gap_skills=["Rust"],
        score_reasoning="Strong Python backend engineer, needs Rust.",
        top_selling_points=["5 years Python", "Shipped FastAPI APIs"],
    )
    assert fit.match_score == 85

    # Out of range (too high)
    with pytest.raises(ValidationError):
        FitScoreOutput(
            match_score=105,
            matched_skills=["Python"],
            gap_skills=[],
            score_reasoning="Too high",
            top_selling_points=[],
        )

    # Out of range (too low)
    with pytest.raises(ValidationError):
        FitScoreOutput(
            match_score=-1,
            matched_skills=["Python"],
            gap_skills=[],
            score_reasoning="Negative score",
            top_selling_points=[],
        )


def test_cover_letter_output_validation():
    """Verify that CoverLetterOutput is parsed correctly."""
    letter = CoverLetterOutput(
        subject_line="Backend Engineer Application",
        cover_letter_body="Dear Hiring Manager...",
        key_selling_points_used=["Python expertise"],
        gaps_addressed=["Rust learning"],
    )
    assert letter.subject_line == "Backend Engineer Application"
    assert letter.gaps_addressed == ["Rust learning"]


def test_agent_state_record_step():
    """Verify AgentState record_step mutates step_timings and error list properly."""
    state = AgentState(resume_text="My Resume", job_description="Cool Job")
    assert len(state.step_timings) == 0

    # Successful step
    state.record_step(name="research", duration_ms=120.456, success=True)
    assert len(state.step_timings) == 1
    assert state.step_timings[0].step_name == "research"
    assert state.step_timings[0].duration_ms == 120.46
    assert state.step_timings[0].success is True
    assert len(state.errors) == 0

    # Failed step
    state.record_step(name="fit_scoring", duration_ms=45.1, success=False, error="LLM Timeout")
    assert len(state.step_timings) == 2
    assert state.step_timings[1].success is False
    assert state.step_timings[1].error_message == "LLM Timeout"
    assert len(state.errors) == 1
    assert "[fit_scoring] LLM Timeout" in state.errors
