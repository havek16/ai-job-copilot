# 🚀 AI Job-Application Copilot

A multi-step AI agent that helps you tailor a job application to a specific role. Give it your resume and a job description — it researches the company, scores how well you fit, and drafts a targeted cover letter.

Built as a portfolio project demonstrating production-quality Python engineering: structured LLM outputs, retry logic, graceful failure handling, and a measurable eval harness.

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
        │      └─ llm_client.py    → Groq (Gemini fallback) → ResearchOutput (Pydantic)
        │
        ├─→ Step 2: Fit Scoring    src/steps/fit_scoring_step.py
        │      └─ llm_client.py    → Groq (Gemini fallback) → FitScoreOutput (Pydantic)
        │
        └─→ Step 3: Cover Letter   src/steps/cover_letter_step.py
               └─ llm_client.py    → Groq (Gemini fallback) → CoverLetterOutput (Pydantic)
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
| Structured JSON logging | `src/logger.py` — JSON logs to `logs/agent_YYYY-MM-DD.log` per step |
| Config-driven | `src/config.py` (Pydantic BaseSettings) — all tunables in `.env` |
| Prompts separated | `src/prompts.py` — all prompt templates in one file |
| Eval harness | `eval/run_eval.py` — measurable agreement metric vs hand-labeled dataset |

---

## Setup

### 1. Clone & install

```bash
git clone <repo>
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

## Project Structure

```
ai-job-copilot/
├── main.py                    # Streamlit UI entry point
├── api.py                     # FastAPI app (POST /run-agent)
├── requirements.txt
├── .env.example               # API key template (never commit .env)
├── .gitignore
├── README.md
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
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini fallback model |
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
- **LLM:** Groq API (llama-3.3-70b-versatile) + Google Gemini (fallback)
- **Web Search:** Tavily API
- **Resume Parsing:** pdfplumber
- **Validation:** Pydantic v2
- **Frontend:** Streamlit
- **Logging:** Python `logging` with JSON formatter
