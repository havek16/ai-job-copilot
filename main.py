"""
main.py — Streamlit UI for the AI Job-Application Copilot.

Single-page app that:
  1. Accepts a resume upload (PDF/TXT) and a job description paste
  2. Sends them to the FastAPI backend via httpx
  3. Progressively reveals three result sections:
       - 🔍 Company Research
       - 📊 Fit Analysis
       - ✉️  Cover Letter Draft

Run with:
    streamlit run main.py
    (Requires the FastAPI backend to be running: uvicorn api:app --reload)
"""

import httpx
import streamlit as st

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Job-Application Copilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "http://127.0.0.1:8000"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import Google Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

/* Hero header */
.hero-title {
    text-align: center;
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.hero-subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

/* Card panels */
.result-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(10px);
}

/* Score badge */
.score-badge {
    display: inline-block;
    font-size: 3rem;
    font-weight: 700;
    color: #34d399;
    line-height: 1;
}
.score-label {
    font-size: 0.9rem;
    color: #64748b;
    display: block;
}

/* Skill pill */
.skill-matched {
    display: inline-block;
    background: rgba(52, 211, 153, 0.15);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 20px;
    padding: 2px 12px;
    margin: 3px;
    font-size: 0.82rem;
}
.skill-gap {
    display: inline-block;
    background: rgba(251, 113, 133, 0.15);
    color: #fb7185;
    border: 1px solid rgba(251, 113, 133, 0.3);
    border-radius: 20px;
    padding: 2px 12px;
    margin: 3px;
    font-size: 0.82rem;
}

/* Section headers */
.section-header {
    font-size: 1.3rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* Cover letter text */
.cover-letter-body {
    background: rgba(0, 0, 0, 0.3);
    border-left: 3px solid #a78bfa;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    white-space: pre-wrap;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #cbd5e1;
}

/* Pipeline timing */
.timing-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.82rem;
    color: #64748b;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}

/* Step indicator */
.step-badge {
    background: rgba(167, 139, 250, 0.15);
    border: 1px solid rgba(167, 139, 250, 0.3);
    color: #a78bfa;
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* Error banner */
.error-banner {
    background: rgba(251, 113, 133, 0.1);
    border: 1px solid rgba(251, 113, 133, 0.3);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #fb7185;
    font-size: 0.9rem;
}

/* Input labels */
.stTextArea label, .stFileUploader label {
    color: #94a3b8 !important;
    font-size: 0.9rem;
}

/* Button */
.stButton > button {
    background: linear-gradient(90deg, #7c3aed, #2563eb);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 0.6rem 2.5rem;
    font-size: 1rem;
    font-weight: 600;
    width: 100%;
    transition: opacity 0.2s;
}
.stButton > button:hover {
    opacity: 0.9;
    border: none;
}
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🚀 AI Job-Application Copilot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Research • Fit Score • Cover Letter — fully automated, in seconds</div>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ── Input section ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("#### 📄 Your Resume")
    resume_file = st.file_uploader(
        "Upload your resume (PDF or TXT)",
        type=["pdf", "txt"],
        help="Text-based PDFs work best. Scanned image PDFs are not supported.",
        key="resume_uploader",
    )
    if resume_file:
        st.success(f"✅ {resume_file.name} uploaded ({resume_file.size:,} bytes)")

with col_right:
    st.markdown("#### 📋 Job Description")
    job_description = st.text_area(
        "Paste the full job description here",
        height=220,
        placeholder="Copy and paste the complete job description from the company website or LinkedIn...",
        key="jd_input",
    )
    if job_description:
        word_count = len(job_description.split())
        st.caption(f"{word_count} words")

st.markdown("")
run_col = st.columns([1, 2, 1])[1]
with run_col:
    run_btn = st.button("⚡ Run Copilot", key="run_btn", use_container_width=True)


# ── Helper renderers ──────────────────────────────────────────────────────────

def render_research(data: dict) -> None:
    st.markdown('<div class="section-header">🔍 Company Research</div>', unsafe_allow_html=True)

    if data.get("research_skipped"):
        st.warning("⚠️ Web search was unavailable — summary based on JD text only.")

    st.markdown(f"**{data.get('company_name', 'Unknown')}**")
    st.markdown(data.get("company_summary", ""))

    news = data.get("recent_news", [])
    if news:
        st.markdown("**Recent News**")
        for item in news:
            st.markdown(f"- {item}")

    culture = data.get("culture_signals", [])
    if culture:
        st.markdown("**Culture Signals**")
        for signal in culture:
            st.markdown(f"- {signal}")


def render_fit_score(data: dict) -> None:
    st.markdown('<div class="section-header">📊 Fit Analysis</div>', unsafe_allow_html=True)

    score = data.get("match_score", 0)
    color = "#34d399" if score >= 70 else "#fbbf24" if score >= 45 else "#fb7185"

    st.markdown(
        f'<span class="score-badge" style="color:{color}">{score}</span>'
        f'<span class="score-label">/ 100 match score</span>',
        unsafe_allow_html=True,
    )

    # Score bar
    st.progress(score / 100)

    st.markdown(f"*{data.get('score_reasoning', '')}*")

    col_m, col_g = st.columns(2)
    with col_m:
        st.markdown("**✅ Matched Skills**")
        pills = "".join(
            f'<span class="skill-matched">{s}</span>'
            for s in data.get("matched_skills", [])
        )
        st.markdown(pills or "*None identified*", unsafe_allow_html=True)

    with col_g:
        st.markdown("**⚠️ Gap Skills**")
        pills = "".join(
            f'<span class="skill-gap">{s}</span>'
            for s in data.get("gap_skills", [])
        )
        st.markdown(pills or "*No major gaps*", unsafe_allow_html=True)

    selling = data.get("top_selling_points", [])
    if selling:
        st.markdown("**🏆 Your Top Selling Points**")
        for sp in selling:
            st.markdown(f"- {sp}")


def render_cover_letter(data: dict) -> None:
    st.markdown('<div class="section-header">✉️ Cover Letter Draft</div>', unsafe_allow_html=True)

    subject = data.get("subject_line", "")
    if subject:
        st.markdown(f"**Subject:** `{subject}`")

    body = data.get("cover_letter_body", "")
    st.markdown(
        f'<div class="cover-letter-body">{body}</div>',
        unsafe_allow_html=True,
    )

    gaps_addressed = data.get("gaps_addressed", [])
    if gaps_addressed:
        with st.expander("Gaps acknowledged in this letter"):
            for g in gaps_addressed:
                st.markdown(f"- {g}")

    # Copy button (Streamlit native clipboard)
    st.code(body, language=None)
    st.caption("☝️ Use the copy icon above to grab the full letter.")


def render_timings(step_timings: list[dict], total_ms: float) -> None:
    with st.expander("⏱ Pipeline Timings", expanded=False):
        for step in step_timings:
            status_icon = "✅" if step.get("success") else "❌"
            st.markdown(
                f'<div class="timing-row">'
                f'<span>{status_icon} {step["step_name"]}</span>'
                f'<span>{step["duration_ms"]:.0f} ms</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="timing-row" style="font-weight:600; color:#94a3b8; border:none;">'
            f'<span>Total</span><span>{total_ms:.0f} ms</span></div>',
            unsafe_allow_html=True,
        )


# ── Run the agent ─────────────────────────────────────────────────────────────

if run_btn:
    # Input validation
    if not resume_file:
        st.error("Please upload your resume before running.")
        st.stop()
    if not job_description or not job_description.strip():
        st.error("Please paste a job description before running.")
        st.stop()
    if len(job_description.strip()) < 50:
        st.error("The job description seems too short. Please paste the complete JD.")
        st.stop()

    st.markdown("---")
    st.markdown("### 🤖 Agent Output")

    with st.status("Running AI pipeline…", expanded=True) as status_widget:
        st.write("📡 Step 1 / 3 — Researching company…")

        # Build multipart request
        try:
            response = httpx.post(
                f"{API_BASE}/run-agent",
                files={"resume_file": (resume_file.name, resume_file.getvalue(), resume_file.type)},
                data={"job_description": job_description},
                timeout=120,  # 2 min — web search + 3 LLM calls can take a while
            )
            response.raise_for_status()
            result = response.json()
        except httpx.ConnectError:
            st.error(
                "❌ Cannot connect to the backend API. "
                "Make sure it's running: `uvicorn api:app --reload`"
            )
            st.stop()
        except httpx.TimeoutException:
            st.error("❌ Request timed out after 2 minutes. Try again.")
            st.stop()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            st.error(f"❌ API error: {detail}")
            st.stop()

        status_widget.update(label="✅ Pipeline complete!", state="complete")

    # ── Render errors (if any) ────────────────────────────────────────────
    if result.get("errors"):
        for err in result["errors"]:
            st.markdown(
                f'<div class="error-banner">⚠️ {err}</div>',
                unsafe_allow_html=True,
            )

    # ── Render results in expandable sections ─────────────────────────────
    if result.get("research"):
        with st.expander("🔍 Company Research", expanded=True):
            render_research(result["research"])

    if result.get("fit_score"):
        with st.expander("📊 Fit Analysis", expanded=True):
            render_fit_score(result["fit_score"])
    else:
        st.warning("Fit scoring was not available for this run.")

    if result.get("cover_letter"):
        with st.expander("✉️ Cover Letter Draft", expanded=True):
            render_cover_letter(result["cover_letter"])
    else:
        st.warning("Cover letter generation was not available for this run.")

    # ── Pipeline timing footer ────────────────────────────────────────────
    render_timings(
        result.get("step_timings", []),
        result.get("total_duration_ms", 0),
    )

# ── Sidebar: help & links ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ℹ️ About")
    st.markdown(
        "AI Job-Application Copilot is a multi-step agent pipeline built with "
        "FastAPI, Groq, Gemini, and Tavily.\n\n"
        "**Steps:**\n"
        "1. 🔍 Company Research\n"
        "2. 📊 Fit Scoring\n"
        "3. ✉️ Cover Letter\n\n"
        "All LLM outputs are Pydantic-validated. "
        "Web search failure is handled gracefully."
    )
    st.markdown("---")
    st.markdown("**API Docs:** [localhost:8000/docs](http://localhost:8000/docs)")
    st.markdown("**Health:** [localhost:8000/health](http://localhost:8000/health)")
