"""
prompts.py — All LLM prompt templates for the AI Job-Application Copilot.

Keeping prompts in one place makes them easy to version, iterate on,
and review — especially important for an interview where you want to
explain your prompt design choices without hunting through multiple files.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Shared system prompt prefix
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_BASE = (
    "You are an expert career coach and talent acquisition specialist with 15+ years "
    "of experience. You give precise, honest, and actionable advice. "
    "You always respond with valid JSON that matches the schema you are given. "
    "Do not include markdown fences, explanations, or any text outside the JSON object."
)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Company Research
# ─────────────────────────────────────────────────────────────────────────────

RESEARCH_SYSTEM = SYSTEM_BASE

def research_prompt(job_description: str, search_snippets: str) -> str:
    """
    Builds the user prompt for the Research step.

    Args:
        job_description: The raw JD text pasted by the user.
        search_snippets: Concatenated web search results, or empty string if
                         search was unavailable.
    """
    search_section = (
        f"Web search results about the company:\n{search_snippets}"
        if search_snippets.strip()
        else "Web search was unavailable. Infer company details from the job description only."
    )

    return f"""Analyze the following job description and web search results, then return a JSON object.

JOB DESCRIPTION:
{job_description}

{search_section}

Return a JSON object with EXACTLY these fields:
{{
  "company_name": "<name of the hiring company>",
  "company_summary": "<2-3 sentences: what the company does, its stage/size if known>",
  "recent_news": ["<news item 1>", "<news item 2>"],
  "culture_signals": ["<signal 1>", "<signal 2>"],
  "research_skipped": <true if search was unavailable, false otherwise>
}}

Limit recent_news to at most 3 items. Limit culture_signals to at most 4 items.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Fit Scoring
# ─────────────────────────────────────────────────────────────────────────────

FIT_SCORE_SYSTEM = SYSTEM_BASE

def fit_score_prompt(resume_text: str, job_description: str, company_context: str) -> str:
    """
    Builds the user prompt for the Fit Scoring step.

    Scoring rubric (baked into the prompt for consistency):
      - 80-100: Strong match, most requirements met
      - 60-79:  Solid candidate, a few gaps
      - 40-59:  Partial match, notable gaps
      - 20-39:  Weak match, significant retooling needed
      - 0-19:   Not a fit
    """
    return f"""You are evaluating a job applicant's resume against a job description.

COMPANY CONTEXT:
{company_context}

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

Score the fit using this rubric:
- 80-100: Strong match, most requirements met
- 60-79:  Solid candidate, a few gaps
- 40-59:  Partial match, notable gaps
- 20-39:  Weak match, significant retooling needed
- 0-19:   Not a fit

Return a JSON object with EXACTLY these fields:
{{
  "match_score": <integer 0-100>,
  "matched_skills": ["<skill 1>", "<skill 2>", ...],
  "gap_skills": ["<missing skill 1>", ...],
  "score_reasoning": "<2-3 sentences explaining the score>",
  "top_selling_points": ["<point 1>", "<point 2>", "<point 3>"]
}}

Be honest and specific. Use exact skill names from both documents. Do not pad the matched list.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Cover Letter
# ─────────────────────────────────────────────────────────────────────────────

COVER_LETTER_SYSTEM = SYSTEM_BASE

def cover_letter_prompt(
    resume_text: str,
    job_description: str,
    company_name: str,
    company_summary: str,
    culture_signals: list[str],
    top_selling_points: list[str],
    gap_skills: list[str],
) -> str:
    """
    Builds the user prompt for the Cover Letter step.

    Design choice: we pass in the structured outputs from previous steps
    rather than the raw research blob, so the prompt stays focused.
    """
    gaps_note = (
        f"Gaps to acknowledge tactfully: {', '.join(gap_skills)}"
        if gap_skills
        else "No significant gaps to address."
    )

    return f"""Write a tailored cover letter for this job application.

COMPANY: {company_name}
COMPANY OVERVIEW: {company_summary}
CULTURE SIGNALS: {"; ".join(culture_signals)}

JOB DESCRIPTION:
{job_description}

APPLICANT'S RESUME:
{resume_text}

KEY SELLING POINTS TO HIGHLIGHT:
{chr(10).join(f"- {p}" for p in top_selling_points)}

{gaps_note}

Instructions:
1. Write a professional, concise cover letter (3-4 paragraphs, ~300 words).
2. Open with a specific hook referencing the company — not a generic opener.
3. Weave in the key selling points naturally, with concrete evidence from the resume.
4. If there are gap skills, acknowledge them briefly and frame as "actively learning" or "excited to grow in".
5. Close with a clear call to action.
6. Do NOT use filler phrases like "I am writing to express my interest".

Return a JSON object with EXACTLY these fields:
{{
  "subject_line": "<email subject for the application>",
  "cover_letter_body": "<full cover letter text with paragraph breaks using \\n\\n>",
  "key_selling_points_used": ["<point 1>", ...],
  "gaps_addressed": ["<gap 1>", ...]
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Company name extraction (fast/cheap call before web search)
# ─────────────────────────────────────────────────────────────────────────────

EXTRACT_COMPANY_SYSTEM = "You extract company names from text. Reply with only the company name, nothing else."

def extract_company_prompt(job_description: str) -> str:
    return (
        f"What is the name of the hiring company in the following job description? "
        f"Reply with ONLY the company name.\n\n{job_description[:1000]}"
    )
