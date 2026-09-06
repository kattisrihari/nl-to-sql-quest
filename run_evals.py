"""
run_evals.py — Orchestrates the full eval pipeline.

1. Creates a LangSmith dataset from test_cases.py
2. Runs each test case through the agent
3. Pushes scores as feedback to LangSmith
4. Prints summary + saves JSON report

Usage:
    python run_evals.py                  # full run
    python run_evals.py --category "Core Business"   # single category
    python run_evals.py --dry-run        # validate test cases only, no agent calls
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from evals.test_cases import TEST_CASES
from evals.evaluator import score_result, run_evals

# ── LangSmith setup ────────────────────────────────────────────────────────────
try:
    from langsmith import Client
    ls_client = Client()
    LANGSMITH_ENABLED = True
    print("✅  LangSmith connected")
except Exception as e:
    ls_client = None
    LANGSMITH_ENABLED = False
    print(f"⚠️   LangSmith not available: {e}")


DATASET_NAME = "hotel-nl2sql-evals"


# ── LangSmith dataset management ──────────────────────────────────────────────

def get_or_create_dataset():
    """Get existing dataset or create new one in LangSmith."""
    if not LANGSMITH_ENABLED:
        return None
    try:
        datasets = list(ls_client.list_datasets(dataset_name=DATASET_NAME))
        if datasets:
            print(f"  Using existing dataset: {DATASET_NAME}")
            return datasets[0]
        else:
            dataset = ls_client.create_dataset(
                dataset_name=DATASET_NAME,
                description="Hotel NL2SQL agent evaluation suite — 30 test cases across 9 categories",
            )
            print(f"  Created new dataset: {DATASET_NAME}")
            return dataset
    except Exception as e:
        print(f"  Dataset error: {e}")
        return None


def push_examples_to_dataset(dataset):
    """Push test cases as examples to LangSmith dataset."""
    if not LANGSMITH_ENABLED or not dataset:
        return
    try:
        existing = list(ls_client.list_examples(dataset_id=dataset.id))
        if len(existing) >= len(TEST_CASES):
            print(f"  Dataset already has {len(existing)} examples — skipping push")
            return

        inputs  = [{"question": tc["question"]} for tc in TEST_CASES]
        outputs = [{
            "expect_blocked":    tc["expect_blocked"],
            "expect_sql":        tc["expect_sql"],
            "must_contain":      tc["must_contain"],
            "must_not_contain":  tc["must_not_contain"],
            "category":          tc["category"],
            "notes":             tc["notes"],
        } for tc in TEST_CASES]

        ls_client.create_examples(
            inputs=inputs,
            outputs=outputs,
            dataset_id=dataset.id,
        )
        print(f"  Pushed {len(TEST_CASES)} examples to LangSmith dataset")
    except Exception as e:
        print(f"  Failed to push examples: {e}")


def push_run_results(results: list, run_id: str):
    """Push eval scores as experiment results to LangSmith."""
    if not LANGSMITH_ENABLED or not ls_client:
        return
    try:
        for result in results:
            ls_client.create_feedback(
                run_id=run_id,
                key="eval_score",
                score=result["total"] / result["max"],
                comment=json.dumps({
                    "test_id":          result["id"],
                    "category":         result["category"],
                    "passed":           result["passed"],
                    "scores":           result["scores"],
                    "latency_s":        result["latency_s"],
                    "missing_keywords": result["missing_keywords"],
                    "found_bad_words":  result["found_bad_words"],
                })
            )
        print(f"  Pushed {len(results)} feedback scores to LangSmith")
    except Exception as e:
        print(f"  LangSmith feedback push failed: {e}")


# ── Dry run — validate test cases only ────────────────────────────────────────

def dry_run():
    """Validate test case structure without running the agent."""
    print("\n── Dry run — validating test cases ────────────────────────────\n")
    errors = []
    for tc in TEST_CASES:
        for field in ["id", "category", "question", "must_contain",
                      "must_not_contain", "expect_sql", "expect_blocked", "notes"]:
            if field not in tc:
                errors.append(f"{tc.get('id','?')} missing field: {field}")

    if errors:
        print("❌  Validation errors:")
        for e in errors:
            print(f"   {e}")
    else:
        print(f"✅  All {len(TEST_CASES)} test cases valid")
        from collections import Counter
        cats = Counter(tc["category"] for tc in TEST_CASES)
        for cat, count in cats.items():
            print(f"   {cat:<25} {count} cases")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Hotel NL2SQL Eval Runner")
    parser.add_argument("--category", type=str, help="Run only this category")
    parser.add_argument("--dry-run",  action="store_true", help="Validate only")
    parser.add_argument("--id",       type=str, help="Run single test case by ID e.g. TC01")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    # Filter test cases
    cases = TEST_CASES
    if args.category:
        cases = [tc for tc in TEST_CASES if tc["category"] == args.category]
        print(f"\nFiltered to category: {args.category} ({len(cases)} cases)")
    if args.id:
        cases = [tc for tc in TEST_CASES if tc["id"] == args.id]
        print(f"\nFiltered to ID: {args.id}")

    if not cases:
        print("No matching test cases found.")
        return

    # LangSmith dataset setup
    print("\n── LangSmith setup ─────────────────────────────────────────────")
    dataset = get_or_create_dataset()
    push_examples_to_dataset(dataset)

    # Run evals
    print()
    summary = run_evals(cases)

    # Push to LangSmith
    if LANGSMITH_ENABLED and summary.get("results"):
        print("\n── Pushing results to LangSmith ────────────────────────────────")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        push_run_results(summary["results"], run_id)
        print(f"\n  View results: https://smith.langchain.com")

    # Final summary line
    pct = summary.get("overall_pct", 0)
    passed = summary.get("passed", 0)
    total  = summary.get("total", 0)
    emoji  = "🟢" if pct >= 90 else "🟡" if pct >= 75 else "🔴"
    print(f"\n{emoji}  Final score: {passed}/{total} passed ({pct}%)\n")


if __name__ == "__main__":
    main()
