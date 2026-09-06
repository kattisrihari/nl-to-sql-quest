"""
evaluator.py — Runs each test case through the agent and scores it.

Scoring per test case (4 points max):
  1. scope_correct   — blocked when expected, or passed when expected
  2. sql_correct     — SQL generated when expected, absent when blocked
  3. answer_quality  — all must_contain strings found in answer
  4. no_hallucination— no must_not_contain strings found in answer

Usage:
    python evals/evaluator.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from src.agent.graph import run_query_full
from evals.test_cases import TEST_CASES

# ── LangSmith client (optional — gracefully skips if not configured) ──────────
try:
    from langsmith import Client
    ls_client = Client()
    LANGSMITH_ENABLED = True
    print("✅  LangSmith connected")
except Exception as e:
    ls_client = None
    LANGSMITH_ENABLED = False
    print(f"⚠️   LangSmith not connected ({e}) — running locally only")


# ── Scorer ─────────────────────────────────────────────────────────────────────

def score_result(tc: dict, state: dict, latency: float) -> dict:
    """Score one test case. Returns a result dict with scores and details."""

    answer      = (state.get("answer") or "").lower()
    sql         = (state.get("sql") or "")
    scope_blocked = state.get("scope_blocked", False)
    exec_failed   = state.get("execution_failed", False)

    scores = {}

    # 1. Scope correct — was blocking behaviour as expected?
    if tc["expect_blocked"]:
        scores["scope_correct"] = 1 if scope_blocked else 0
    else:
        scores["scope_correct"] = 1 if not scope_blocked else 0

    # 2. SQL correct — was SQL generated (or absent) as expected?
    if tc["expect_sql"]:
        scores["sql_correct"] = 1 if (sql and len(sql.strip()) > 10) else 0
    else:
        scores["sql_correct"] = 1 if not sql or len(sql.strip()) < 10 else 0

    # 3. Answer quality — all must_contain present?
    must_contain = tc.get("must_contain", [])
    if must_contain:
        hits = [kw.lower() for kw in must_contain if kw.lower() in answer]
        scores["answer_quality"] = 1 if len(hits) == len(must_contain) else 0
        missing = [kw for kw in must_contain if kw.lower() not in answer]
    else:
        scores["answer_quality"] = 1  # no constraint = auto pass
        missing = []

    # 4. No hallucination — none of must_not_contain present?
    must_not = tc.get("must_not_contain", [])
    if must_not:
        found_bad = [kw.lower() for kw in must_not if kw.lower() in answer]
        scores["no_hallucination"] = 1 if not found_bad else 0
    else:
        scores["no_hallucination"] = 1
        found_bad = []

    total      = sum(scores.values())
    max_score  = 4
    passed     = total == max_score

    return {
        "id":               tc["id"],
        "category":         tc["category"],
        "question":         tc["question"],
        "answer":           state.get("answer", "")[:300],  # truncate for display
        "sql":              sql[:200] if sql else "",
        "scores":           scores,
        "total":            total,
        "max":              max_score,
        "passed":           passed,
        "latency_s":        round(latency, 2),
        "missing_keywords": missing,
        "found_bad_words":  found_bad,
        "notes":            tc.get("notes", ""),
    }


# ── LangSmith logging ──────────────────────────────────────────────────────────

def log_to_langsmith(result: dict, dataset_name: str, run_id: str):
    """Log a single eval result as feedback to LangSmith."""
    if not LANGSMITH_ENABLED or not ls_client:
        return
    try:
        ls_client.create_feedback(
            run_id=run_id,
            key="eval_score",
            score=result["total"] / result["max"],
            comment=json.dumps({
                "passed":           result["passed"],
                "scores":           result["scores"],
                "missing_keywords": result["missing_keywords"],
                "found_bad_words":  result["found_bad_words"],
                "latency_s":        result["latency_s"],
            })
        )
    except Exception as e:
        print(f"    LangSmith log failed: {e}")


# ── Main runner ────────────────────────────────────────────────────────────────

def run_evals(test_cases: list = None, verbose: bool = True) -> dict:
    """Run all test cases and return aggregated results."""

    if test_cases is None:
        test_cases = TEST_CASES

    results     = []
    run_id      = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"hotel-nl2sql-evals-{run_id}"

    print(f"\n{'='*65}")
    print(f"  Hotel NL2SQL Eval Run — {run_id}")
    print(f"  {len(test_cases)} test cases")
    print(f"{'='*65}\n")

    for i, tc in enumerate(test_cases, 1):
        print(f"[{i:02d}/{len(test_cases)}] {tc['id']} — {tc['question'][:60]}...")

        t0 = time.time()
        try:
            state = run_query_full(tc["question"])
        except Exception as e:
            print(f"         ❌  Agent crashed: {e}")
            state = {"answer": f"CRASH: {e}", "sql": "", "scope_blocked": False, "execution_failed": True}

        latency = time.time() - t0
        result  = score_result(tc, state, latency)
        results.append(result)

        # Print result line
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"         {status} {result['total']}/{result['max']} | {latency:.2f}s | {tc['category']}")

        if not result["passed"] and verbose:
            if result["missing_keywords"]:
                print(f"         Missing: {result['missing_keywords']}")
            if result["found_bad_words"]:
                print(f"         Bad words found: {result['found_bad_words']}")
            if result["scores"]["scope_correct"] == 0:
                print(f"         Scope mismatch — expected_blocked={tc['expect_blocked']}")
            if result["scores"]["sql_correct"] == 0:
                print(f"         SQL mismatch — expected_sql={tc['expect_sql']}, got='{result['sql'][:50]}'")

        print()

    # ── Aggregate ──────────────────────────────────────────────────────────────
    total_passed  = sum(1 for r in results if r["passed"])
    total_points  = sum(r["total"] for r in results)
    max_points    = sum(r["max"] for r in results)
    overall_pct   = round(total_points / max_points * 100, 1)
    avg_latency   = round(sum(r["latency_s"] for r in results) / len(results), 2)

    # By category
    from collections import defaultdict
    by_cat = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        by_cat[r["category"]]["total"] += 1
        if r["passed"]:
            by_cat[r["category"]]["passed"] += 1

    print(f"\n{'='*65}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*65}")
    print(f"  Overall:     {total_passed}/{len(results)} passed ({overall_pct}%)")
    print(f"  Points:      {total_points}/{max_points}")
    print(f"  Avg latency: {avg_latency}s")
    print(f"\n  By category:")
    for cat, data in sorted(by_cat.items()):
        pct = round(data["passed"] / data["total"] * 100)
        bar = "█" * data["passed"] + "░" * (data["total"] - data["passed"])
        print(f"  {cat:<25} {bar}  {data['passed']}/{data['total']} ({pct}%)")

    # Failed cases
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n  Failed cases:")
        for r in failed:
            print(f"  ❌ {r['id']} — {r['question'][:55]}...")

    print(f"\n{'='*65}\n")

    # ── Save results to JSON ───────────────────────────────────────────────────
    output_path = Path(__file__).parent / f"eval_results_{run_id}.json"
    with open(output_path, "w") as f:
        json.dump({
            "run_id":        run_id,
            "timestamp":     datetime.now().isoformat(),
            "summary": {
                "total_cases":  len(results),
                "passed":       total_passed,
                "overall_pct":  overall_pct,
                "total_points": total_points,
                "max_points":   max_points,
                "avg_latency":  avg_latency,
            },
            "by_category":   dict(by_cat),
            "results":       results,
        }, f, indent=2)
    print(f"  Results saved: {output_path.name}")

    return {
        "passed":      total_passed,
        "total":       len(results),
        "overall_pct": overall_pct,
        "results":     results,
    }


if __name__ == "__main__":
    # Run specific categories only — comment out to run all
    # FILTER = ["Core Business", "Scope Blocking"]
    # cases = [tc for tc in TEST_CASES if tc["category"] in FILTER]
    # run_evals(cases)

    run_evals()
