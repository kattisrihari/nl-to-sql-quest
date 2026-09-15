"""
nodes.py — LangGraph node functions for the NL2SQL agent.

Each function is a node in the graph:
  1. scope_check  → blocks out-of-scope questions
  2. generate_sql → calls Claude to write SQL from the user's question
  3. validate_sql → checks SQL safety and syntax
  4. execute_sql  → runs SQL against the DB
  5. synthesize   → calls Claude to narrate the result in plain English
  6. fail_node    → friendly error message

State flows through all nodes as a plain dict.
"""

import os
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from src.agent.prompts import SQL_GENERATION_PROMPT, SYNTHESIS_PROMPT
from src.agent.tools import validate_sql, execute_sql

load_dotenv()
INJECTION_PATTERNS = [
   "ignore previous instructions",
    "ignore your instructions", 
    "forget your instructions",
    "forget you are",
    "you are now a",
    "print your source",
    "reveal your prompt",
    "show your system prompt",
    "jailbreak",
    "pretend you are not",
    "DAN mode",
    "unrestricted mode",
]

def sanitize_question(question: str) -> tuple[bool, str]:
    """
    Returns (is_clean, reason).
    Detects prompt injection attempts before hitting the LLM.
    """
    q_lower = question.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in q_lower:
            return False, f"Injection pattern detected: '{pattern}'"
    return True, ""

# ── Scope blocklist ────────────────────────────────────────────────────────────
BLOCKED_TOPICS = {
    "weather", "temperature", "rainfall", "climate", "forecast",
    "nfl", "nba", "mlb", "nhl", "cricket", "football", "soccer", "sports",
    "news", "politics", "election", "stock", "crypto", "bitcoin", "finance",
    "recipe", "cooking", "food", "restaurant",
    "movie", "music", "song", "lyrics", "netflix",
    "export all", "dump", "download all", "print all",
    "who is", "what is the capital", "translate", "define",
    "kobe", "jordan", "mj", "celebrity", "who were", "are they friends",
    "ignore previous", "ignore instructions", "forget you",
    "forget your", "print source", "system prompt",
    "you are now", "new instructions", "disregard",
    "act as", "pretend you are", "jailbreak",
    "unrestricted", "bypass", "override instructions",
    "reveal your", "show your prompt", "print your",
}

def is_in_scope(question: str) -> bool:
    q = question.lower()
    if any(word in q for word in BLOCKED_TOPICS):
        return False
    return True

# ── LLM setup ─────────────────────────────────────────────────────────────────
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=1000,
    temperature=0,
)

MAX_RETRIES = 2

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace the LLM sometimes adds."""
    raw = re.sub(r"```sql|```", "", raw, flags=re.IGNORECASE)
    return raw.strip()


# ── Node 0: Scope check ────────────────────────────────────────────────────────

def scope_check_node(state: dict) -> dict:
    # Check injection first
    is_clean, reason = sanitize_question(state["question"])
    if not is_clean:
        print(f"[scope_check] injection detected: {reason}")
        return {**state, "scope_blocked": True}

    # Then scope check
    if not is_in_scope(state["question"]):
        return {**state, "scope_blocked": True}

    return {**state, "scope_blocked": False}


def route_after_scope(state: dict) -> str:
    if state.get("scope_blocked"):
        return "fail"
    return "generate"


# ── Node 1: Generate SQL ───────────────────────────────────────────────────────

REFUSAL_PHRASES = [
    "cannot be answered", "i cannot", "not possible",
    "no sql", "unable to", "don't have", "not in the database",
]

def generate_sql(state: dict) -> dict:
    # Hard wall — refuse to run if retry cap already hit
    if state.get("retry_count", 0) >= MAX_RETRIES:
        print("[generate_sql] retry cap hit — forcing fail")
        return {**state, "sql": "", "retry_count": MAX_RETRIES}

    question   = state["question"]
    retry      = state.get("retry_count", 0)
    prev_error = state.get("error", "")

    prompt = SQL_GENERATION_PROMPT.format(question=question)
    if retry > 0 and prev_error:
        prompt += (
            f"\n\nYour previous SQL attempt failed. "
            f"Simplify your approach — avoid deeply nested subqueries. "
            f"Use AVG() instead of MEDIAN(). Error was: {prev_error[:100]}"
        )

    response = llm.invoke([HumanMessage(content=prompt)])
    sql = clean_sql(response.content)

    # Detect identical SQL — LLM is stuck, force fail
    if sql == state.get("last_sql", ""):
        print("[generate_sql] identical SQL detected — forcing fail")
        return {**state, "sql": "", "retry_count": MAX_RETRIES}

    # Detect LLM refusal to write SQL
    if any(phrase in sql.lower() for phrase in REFUSAL_PHRASES):
        print("[generate_sql] LLM refused — forcing fail")
        return {**state, "sql": "", "retry_count": MAX_RETRIES}

    print(f"\n[generate_sql] attempt {retry + 1}\n{sql}")
    return {**state, "sql": sql, "last_sql": sql}


# ── Node 2: Validate SQL ───────────────────────────────────────────────────────

def validate_node(state: dict) -> dict:
    """Run safety + syntax checks. Sets 'valid' flag for the graph router."""
    sql = state.get("sql", "")
    valid, message = validate_sql(sql)
    print(f"[validate_sql] valid={valid} | {message}")
    return {**state, "valid": valid, "error": message if not valid else ""}


# ── Node 3: Execute SQL ────────────────────────────────────────────────────────

def execute_node(state: dict) -> dict:
    sql = state.get("sql", "")
    ok, result = execute_sql(sql)
    print(f"[execute_sql] ok={ok}")

    if not ok:
        return {**state, "execution_failed": True, "error": result, "results": ""}

    results_capped = result[:3000] if len(result) > 3000 else result
    return {**state, "execution_failed": False, "results": results_capped}

# ── Node 4: Synthesize answer ─────────────────────────────────────────────────

def synthesize(state: dict) -> dict:
    """Ask Claude to turn raw SQL results into a plain-English answer."""
    question = state["question"]
    results  = state.get("results", "")

    prompt = SYNTHESIS_PROMPT.format(question=question, results=results)
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip()
    print(f"[synthesize]\n{answer}")
    return {**state, "answer": answer}


# ── Node 5: Failure fallback ───────────────────────────────────────────────────

def fail_node(state: dict) -> dict:
    if state.get("scope_blocked"):
        answer = (
            "I can only answer questions about hotel bookings data — "
            "regions, hotels, customers, bookings, revenue, and occupancy. "
            "Please ask something related to the hotel database."
        )
    else:
        answer = (
            "I wasn't able to generate a valid query for that question. "
            "Could you try rephrasing it? Mention specific time periods, "
            "regions, or hotel categories you're interested in."
        )
    print(f"[fail_node] scope_blocked={state.get('scope_blocked')}")
    return {**state, "answer": answer}


# ── Router: after execution ────────────────────────────────────────────────────

def route_after_execution(state: dict) -> str:
    if state.get("execution_failed"):
        return "fail"
    return "synthesize"


# ── Router: after validation ───────────────────────────────────────────────────

def route_after_validation(state: dict) -> str:
    if state.get("valid"):
        return "execute"

    retry = state.get("retry_count", 0) + 1
    if retry >= MAX_RETRIES:
        return "fail"

    state["retry_count"] = retry
    return "retry"
