"""
run_eval.py — Evaluation harness for the Fit Scoring step.

Runs the fit_scoring_step against 10 hand-labeled (JD, resume) pairs
and reports how closely the agent's scores match expected scores.

Agreement metric: within ±10 points counts as a "match".

Usage:
    python eval/run_eval.py [--output eval/results.md]

Design notes:
  - Calls fit_scoring_step.execute() directly (no UI, no web search).
  - Web search is skipped intentionally — we want to isolate scoring quality.
  - Each eval entry uses a short resume_snippet, not a full PDF.
  - Results are written to a markdown file for committing to the repo.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so src.* imports work
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.schemas import AgentState, ResearchOutput
from src.steps import fit_scoring_step


def load_eval_set(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_single(entry: dict) -> dict:
    """Run fit scoring for a single eval entry. Returns a result dict."""
    # Build a minimal AgentState — no PDF parsing, no web search
    state = AgentState(
        resume_text=entry["resume_snippet"],
        job_description=entry["job_description"],
        # Provide stub research so the step has company context
        research=ResearchOutput(
            company_name=entry.get("company", "Unknown"),
            company_summary=f"{entry.get('company', 'Company')} — {entry.get('job_title', 'role')}",
        ),
    )

    t0 = time.perf_counter()
    state = fit_scoring_step.execute(state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    actual_score = state.fit_score.match_score if state.fit_score else None
    expected_score = entry["expected_score"]

    within_10 = (
        abs(actual_score - expected_score) <= 10
        if actual_score is not None
        else False
    )
    error = state.errors[-1] if state.errors else None

    return {
        "id": entry["id"],
        "job_title": entry["job_title"],
        "company": entry.get("company", ""),
        "expected_score": expected_score,
        "actual_score": actual_score,
        "delta": abs(actual_score - expected_score) if actual_score is not None else None,
        "within_10": within_10,
        "elapsed_ms": round(elapsed_ms, 1),
        "error": error,
        "notes": entry.get("notes", ""),
        "matched_skills": state.fit_score.matched_skills if state.fit_score else [],
        "gap_skills": state.fit_score.gap_skills if state.fit_score else [],
        "reasoning": state.fit_score.score_reasoning if state.fit_score else "",
    }


def format_results_markdown(results: list[dict], run_time_s: float) -> str:
    """Format results as a markdown report."""
    total = len(results)
    scored = [r for r in results if r["actual_score"] is not None]
    agreed = [r for r in scored if r["within_10"]]
    mae = (
        sum(r["delta"] for r in scored) / len(scored)
        if scored else float("nan")
    )
    agreement_pct = len(agreed) / total * 100 if total else 0

    lines = [
        "# Eval Results — Fit Scoring Step",
        "",
        f"**Run date:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        f"**Total eval entries:** {total}",
        f"**Scored successfully:** {len(scored)} / {total}",
        f"**Agreement (±10 pts):** {len(agreed)} / {total} = **{agreement_pct:.1f}%**",
        f"**Mean Absolute Error:** {mae:.1f} points",
        f"**Total eval time:** {run_time_s:.1f}s",
        "",
        "## Per-Entry Results",
        "",
        "| ID | Role | Company | Expected | Actual | Δ | ✓ | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        check = "✅" if r["within_10"] else "❌"
        actual = str(r["actual_score"]) if r["actual_score"] is not None else "ERR"
        delta = str(r["delta"]) if r["delta"] is not None else "—"
        lines.append(
            f"| {r['id']} | {r['job_title']} | {r['company']} "
            f"| {r['expected_score']} | {actual} | {delta} | {check} | {r['notes']} |"
        )

    lines += [
        "",
        "## Detailed Reasoning",
        "",
    ]
    for r in results:
        lines.append(f"### {r['id']} — {r['job_title']} @ {r['company']}")
        lines.append(f"- **Expected:** {r['expected_score']}  |  **Actual:** {r.get('actual_score', 'N/A')}")
        lines.append(f"- **Reasoning:** {r.get('reasoning', 'N/A')}")
        matched = ", ".join(r.get("matched_skills", [])) or "None"
        gaps = ", ".join(r.get("gap_skills", [])) or "None"
        lines.append(f"- **Matched:** {matched}")
        lines.append(f"- **Gaps:** {gaps}")
        if r.get("error"):
            lines.append(f"- **Error:** {r['error']}")
        lines.append("")

    return "\n".join(lines)


def main(output_path: str = "eval/results.md") -> None:
    eval_path = Path(__file__).parent / "eval_set.json"
    eval_set = load_eval_set(eval_path)

    print(f"\n{'='*60}")
    print(f"  AI Job-Application Copilot — Eval Harness")
    print(f"  Running {len(eval_set)} eval entries...")
    print(f"{'='*60}\n")

    results = []
    t_start = time.perf_counter()

    for i, entry in enumerate(eval_set, start=1):
        print(f"[{i:02d}/{len(eval_set)}] {entry['id']} — {entry['job_title']} @ {entry.get('company', '?')}")
        try:
            result = run_single(entry)
            status = "✅" if result["within_10"] else "❌"
            actual = result["actual_score"] if result["actual_score"] is not None else "ERR"
            print(
                f"       Expected: {result['expected_score']:3d}  "
                f"Actual: {str(actual):3}  "
                f"Δ: {str(result['delta'] or '—'):3}  {status}  "
                f"({result['elapsed_ms']:.0f}ms)"
            )
        except Exception as err:
            print(f"       FAILED: {err}")
            result = {
                "id": entry["id"],
                "job_title": entry["job_title"],
                "company": entry.get("company", ""),
                "expected_score": entry["expected_score"],
                "actual_score": None,
                "delta": None,
                "within_10": False,
                "elapsed_ms": 0,
                "error": str(err),
                "notes": entry.get("notes", ""),
                "matched_skills": [],
                "gap_skills": [],
                "reasoning": "",
            }
        results.append(result)

    run_time_s = time.perf_counter() - t_start

    # ── Summary ───────────────────────────────────────────────────────────────
    scored = [r for r in results if r["actual_score"] is not None]
    agreed = [r for r in scored if r["within_10"]]
    mae = sum(r["delta"] for r in scored) / len(scored) if scored else float("nan")

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Agreement (±10 pts):  {len(agreed)}/{len(results)} = {len(agreed)/len(results)*100:.1f}%")
    print(f"  Mean Absolute Error:  {mae:.1f} points")
    print(f"  Total time:           {run_time_s:.1f}s")
    print(f"{'='*60}\n")

    # ── Write markdown results ────────────────────────────────────────────────
    md = format_results_markdown(results, run_time_s)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    print(f"Results written to: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the fit-scoring eval harness")
    parser.add_argument(
        "--output",
        default="eval/results.md",
        help="Path to write the markdown results file",
    )
    args = parser.parse_args()
    main(output_path=args.output)
