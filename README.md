# 🚀 AI Job-Application Copilot

[![CI](https://github.com/havek16/ai-job-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/havek16/ai-job-copilot/actions/workflows/ci.yml)

A multi-step AI agent that helps you tailor a job application to a specific role. Give it your resume and a job description — it researches the company, scores how well you fit, and drafts a targeted cover letter.

Built as a portfolio project demonstrating **reliability-minded Python engineering**: Pydantic-validated structured LLM outputs, retry/fallback logic across two model providers, graceful degradation when optional tools fail, and a custom offline eval harness.

> **Scope note:** This is a local/demo portfolio app, not a hardened production service. The API has optional key auth (off by default), no rate limiting, and secrets via `.env`. The patterns below are what you'd extend toward production — not claims that every box is already checked.

---

## Architecture

```
User (Streamlit UI :8501)
        │
        ▼  POST /run-agent (multipart)
FastAPI  api.py  (:8000)
        │
        ▼
AgentLoop  src/agent.py
        │
        ├─→ Step 1: Research       src/steps/research_step.py
        │      ├─ web_search.py    → Tavily API (graceful skip if unavailable)
        │      └─ llm_client.py    → Groq (primary) → Gemini (fallback) → Pydantic
        │
        ├─→ Step 2: Fit Scoring    src/steps/fit_scoring_step.py
        │      └─ llm_client.py    → Groq → Gemini fallback → FitScoreOutput
        │
        └─→ Step 3: Cover Letter   src/steps/cover_letter_step.py
               └─ llm_client.py    → Groq → Gemini fallback → CoverLetterOutput
                                                    │
                                            AgentResult (Pydantic)
                                                    │
                                    ◄───────────────┘
                        Streamlit renders 3 sections
```

Each step's output is a validated **Pydantic model** that feeds into the next step. The `AgentState` scratchpad threads through all three steps, accumulating results.

---

## Engineering Highlights

| Practice | Where |
|---|---|
| Structured LLM output | `src/llm_client.py` → every call validated against a Pydantic schema |
| Retry-on-validation-failure | `call_with_retry()` — up to `MAX_RETRIES` (default 2) before graceful failure |
| Groq-first / Gemini fallback | `llm_client.py` — Gemini kicks in if Groq raises any exception |
| Graceful tool failure | `web_search.py` — never raises; logs warning, returns empty list |
| Optional API key auth | `api.py` — enforces `X-API-Key` only when `API_KEY` is set in `.env` |
| Structured JSON logging | `src/logger.py` — JSON logs to `logs/agent_YYYY-MM-DD.log` per step |
| Config-driven | `src/config.py` (Pydantic BaseSettings) — all tunables in `.env` |
| Prompts separated | `src/prompts.py` — all prompt templates in one file |
| Unit/integration tests | `tests/` — pytest suite (schemas, retry logic, API endpoints) |
| CI on push | `.github/workflows/ci.yml` — pytest + Docker build validation |
| Eval harness | `eval/run_eval.py` — measurable agreement metric vs hand-labeled dataset |

---

## Setup

### 1. Clone & install

```bash
git clone https://github.com/havek16/ai-job-copilot.git
cd ai-job-copilot
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and fill in your keys:
#   GROQ_API_KEY   → https://console.groq.com
#   GEMINI_API_KEY → https://aistudio.google.com
#   TAVILY_API_KEY → https://tavily.com (free: 1000 req/month)
```

> **Note:** The app works without `TAVILY_API_KEY` — web search is skipped and the LLM uses only the JD text for company research.

### 3. Run

In two terminals:

```bash
# Terminal 1 — FastAPI backend
uvicorn api:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Streamlit UI
streamlit run main.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Running Tests

```bash
pytest -v
```

The suite covers:

- **Schema validation** — Pydantic models reject out-of-range scores and missing fields
- **Retry / fallback logic** — `call_with_retry()` retries on validation failure and falls back Groq → Gemini
- **API endpoints** — health check, input validation, optional auth, mocked pipeline success
- **Graceful degradation** — web search returns empty results instead of raising

CI runs the same suite on every push to `main`.

---

## Project Structure

```
ai-job-copilot/
├── main.py                    # Streamlit UI entry point
├── api.py                     # FastAPI app (POST /run-agent)
├── requirements.txt
├── pytest.ini
├── .env.example               # API key template (never commit .env)
├── .github/workflows/ci.yml   # GitHub Actions: pytest + Docker builds
├── src/
│   ├── config.py              # Pydantic BaseSettings — all tunables
│   ├── schemas.py             # All Pydantic models (AgentState, outputs)
│   ├── prompts.py             # All LLM prompt templates
│   ├── llm_client.py          # Groq + Gemini client with retry logic
│   ├── logger.py              # JSON structured logger
│   ├── agent.py               # AgentLoop orchestrator
│   ├── tools/
│   │   ├── web_search.py      # Tavily search (graceful skip on failure)
│   │   └── resume_parser.py   # PDF/TXT text extraction (pdfplumber)
│   └── steps/
│       ├── research_step.py   # Step 1: Company research
│       ├── fit_scoring_step.py # Step 2: Resume vs JD fit score
│       └── cover_letter_step.py # Step 3: Tailored cover letter
├── tests/
│   ├── conftest.py            # Shared fixtures and env isolation
│   ├── test_schemas.py        # Pydantic schema validation
│   ├── test_llm_client.py     # Retry logic and provider fallback
│   ├── test_api.py            # FastAPI endpoint tests
│   ├── test_config.py         # Settings defaults and overrides
│   └── test_web_search.py     # Graceful search failure handling
├── logs/                      # JSON log files (generated at runtime)
└── eval/
    ├── eval_set.json          # 10 hand-labeled JD + resume pairs
    ├── run_eval.py            # Eval harness script
    └── results.md             # Last eval run results (commit after running)
```

---

## Running the Eval

```bash
python eval/run_eval.py
```

This runs the fit-scoring step against 10 hand-labeled examples and reports:
- **Agreement %** — how many scores are within ±10 points of the expected score
- **Mean Absolute Error** — average point deviation

Results are written to `eval/results.md`. See [eval/results.md](eval/results.md) for the last committed run.

---

## API Docs

The FastAPI backend auto-generates interactive docs at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Configuration Reference

All settings in `src/config.py`, overridable via `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name (override as newer models ship) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini fallback model |
| `API_KEY` | _(empty)_ | Optional `X-API-Key` for `/run-agent` (off when empty) |
| `TEMPERATURE` | `0.3` | LLM sampling temperature |
| `MAX_TOKENS` | `2048` | Max tokens per LLM response |
| `MAX_RETRIES` | `2` | Retries on Pydantic validation failure |
| `REQUEST_TIMEOUT_S` | `20` | HTTP timeout for API calls |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Example Output

**Fit Score:** 75/100  
**Matched Skills:** Python, PyTorch, MLflow, Docker, Kubernetes  
**Gap Skills:** Distributed systems at scale (Spark/Flink), Fraud/risk ML domain  
**Cover Letter:** Tailored 300-word letter referencing the company's recent Series C and acknowledging the Spark gap as an active learning area.

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **LLM:** Groq API (configurable, default `llama-3.3-70b-versatile`) + Google Gemini fallback (default `gemini-2.5-flash`)
- **Web Search:** Tavily API
- **Resume Parsing:** pdfplumber
- **Validation:** Pydantic v2
- **Testing:** pytest, pytest-mock
- **CI:** GitHub Actions
- **Frontend:** Streamlit
- **Logging:** Python `logging` with JSON formatter

---

## Resume bullet (copy-paste)

> Built a multi-step LLM agent (FastAPI + Streamlit) with Pydantic-validated structured outputs, retry/fallback logic across two model providers, pytest coverage for schemas and API endpoints, CI on push, and a custom offline eval harness measuring fit-scoring accuracy against a hand-labeled dataset.
