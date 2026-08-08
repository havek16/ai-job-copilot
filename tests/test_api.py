import pytest
from fastapi.testclient import TestClient
from src.config import config
from src.schemas import (
    AgentResult,
    ResearchOutput,
    FitScoreOutput,
    CoverLetterOutput,
    StepTiming,
)
from api import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that the health check endpoint returns 200 and 'ok' status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_run_agent_validation_errors():
    """Verify input validation rules for JDs (empty and too short)."""
    # Empty job description
    response = client.post(
        "/run-agent",
        data={"job_description": ""},
        files={"resume_file": ("resume.pdf", b"PDF content", "application/pdf")},
    )
    assert response.status_code == 422
    assert "cannot be empty" in response.json()["detail"].lower()

    # Short job description
    response = client.post(
        "/run-agent",
        data={"job_description": "too short"},
        files={"resume_file": ("resume.pdf", b"PDF content", "application/pdf")},
    )
    assert response.status_code == 422
    assert "too short" in response.json()["detail"].lower()


def test_run_agent_auth_enforced(monkeypatch):
    """Verify that API Key authentication is enforced if configured."""
    # Enforce API Key
    monkeypatch.setattr(config, "API_KEY", "super-secret-production-key")

    long_jd = (
        "This is a longer job description that satisfies the length "
        "requirements of 50 characters to avoid validation errors."
    )

    # Call without header
    response = client.post(
        "/run-agent",
        data={"job_description": long_jd},
        files={"resume_file": ("resume.pdf", b"PDF content", "application/pdf")},
    )
    assert response.status_code == 403
    assert "missing" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    # Call with incorrect header
    response = client.post(
        "/run-agent",
        data={"job_description": long_jd},
        headers={"X-API-Key": "wrong-key"},
        files={"resume_file": ("resume.pdf", b"PDF content", "application/pdf")},
    )
    assert response.status_code == 403
    assert "invalid" in response.json()["detail"].lower()


def test_run_agent_success(mocker):
    """Verify successful run-agent pipeline execution using mocked AgentLoop."""
    mock_result = AgentResult(
        success=True,
        research=ResearchOutput(
            company_name="Mock Corp",
            company_summary="Builds high-quality mock objects.",
            recent_news=["Mock Corp releases new tests"],
            culture_signals=["Excellent testing culture"],
        ),
        fit_score=FitScoreOutput(
            match_score=95,
            matched_skills=["Testing", "Python"],
            gap_skills=[],
            score_reasoning="Candidate has excellent test writing skills.",
            top_selling_points=["Pytest expert", "FastAPI builder"],
        ),
        cover_letter=CoverLetterOutput(
            subject_line="Mock Application for QA Engineer",
            cover_letter_body="Dear Mock Corp, I am excited...",
            key_selling_points_used=["Pytest expert"],
            gaps_addressed=[],
        ),
        step_timings=[
            StepTiming(step_name="research", duration_ms=10.5, success=True),
            StepTiming(step_name="fit_scoring", duration_ms=15.0, success=True),
            StepTiming(step_name="cover_letter", duration_ms=22.3, success=True),
        ],
        errors=[],
        total_duration_ms=47.8,
    )

    # Mock the AgentLoop run method
    mock_run = mocker.patch("src.agent.AgentLoop.run", return_value=mock_result)

    long_jd = (
        "We are looking for a Python Software Engineer to build and maintain "
        "high-quality APIs and write tests using pytest. Apply today!"
    )

    response = client.post(
        "/run-agent",
        data={"job_description": long_jd},
        files={"resume_file": ("resume.txt", b"Mock resume text content", "text/plain")},
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["research"]["company_name"] == "Mock Corp"
    assert res_json["fit_score"]["match_score"] == 95
    assert res_json["total_duration_ms"] == 47.8

    # Assert AgentLoop.run was called with parsed input text
    mock_run.assert_called_once()
