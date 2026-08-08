"""
api.py — FastAPI entry point for the AI Job-Application Copilot.

Endpoints:
  POST /run-agent   — Accepts resume (file) + job description (text),
                      runs the full AgentLoop, returns AgentResult JSON.
  GET  /health      — Simple liveness probe.

The API and Streamlit UI are intentionally separated:
  - The API is independently testable (curl, pytest, Postman).
  - The UI stays thin — just HTTP calls and rendering.
  - This mirrors a real production architecture.

Run with:
    uvicorn api:app --reload --host 127.0.0.1 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.agent import AgentLoop
from src.config import config
from src.logger import get_logger
from src.schemas import AgentResult
from src.tools.resume_parser import parse_resume

logger = get_logger(__name__)


# ── App setup ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "AI Job-Application Copilot API starting",
        extra={"groq_model": config.GROQ_MODEL, "gemini_model": config.GEMINI_MODEL},
    )
    yield
    logger.info("API shutting down")


app = FastAPI(
    title="AI Job-Application Copilot",
    description=(
        "Multi-step agent that researches a company, scores resume fit, "
        "and drafts a tailored cover letter."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Streamlit (localhost:8501) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health_check():
    """Liveness probe — returns 200 if the server is up."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/run-agent", response_model=AgentResult, tags=["agent"])
async def run_agent(
    resume_file: UploadFile = File(..., description="PDF or TXT resume"),
    job_description: str = Form(..., description="Full job description text"),
) -> AgentResult:
    """
    Run the full 3-step job application pipeline.

    Steps:
      1. Research — web search + LLM synthesis of company info
      2. Fit Scoring — resume vs JD comparison (0-100 score)
      3. Cover Letter — tailored draft using all prior context

    Returns structured JSON with all three outputs plus timing metadata.
    """
    logger.info(
        f"Received /run-agent request",
        extra={"filename": resume_file.filename, "jd_length": len(job_description)},
    )

    # ── Validate inputs ───────────────────────────────────────────────────
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="Job description cannot be empty.")

    if len(job_description) < 50:
        raise HTTPException(
            status_code=422,
            detail="Job description seems too short. Please paste the full JD.",
        )

    # ── Parse resume ──────────────────────────────────────────────────────
    try:
        file_bytes = await resume_file.read()
        resume_text = parse_resume(file_bytes, resume_file.filename or "resume.pdf")
    except (ValueError, RuntimeError) as err:
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error parsing resume: {err}")
        raise HTTPException(status_code=500, detail="Failed to parse resume file.")

    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the resume. Is it a text-based PDF?",
        )

    # ── Run the agent ─────────────────────────────────────────────────────
    try:
        agent = AgentLoop()
        result = agent.run(
            resume_text=resume_text,
            job_description=job_description,
        )
        return result
    except Exception as err:
        logger.error(f"AgentLoop raised unexpectedly: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline error: {str(err)}",
        )
