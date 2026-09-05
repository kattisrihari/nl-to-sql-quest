"""
nodes.py — LangGraph node functions for the NL2SQL agent.

Each function is a node in the graph:
  1. generate_sql  → calls Claude to write SQL from the user's question
  2. validate_sql  → checks SQL safety and syntax
  3. execute_sql   → runs SQL against the DB
  4. synthesize    → calls Claude to narrate the result in plain English

State flows through all nodes as a plain dict.
"""

import os
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.prompts import SQL_GENERATION_PROMPT, SYNTHESIS_PROMPT
from src.agent.tools import validate_sql, execute_sql

load_dotenv()

BLOCKED_TOPICS = {
    "weather", "temperature", "rainfall", "climate", "forecast",
    "nfl", "nba", "mlb", "nhl", "cricket", "football", "soccer", "sports",
    "news", "politics", "election", "stock", "crypto", "bitcoin", "finance",
    "recipe", "cooking", "food", "restaurant",
    "movie", "music", "song", "lyrics", "netflix",
    "export all", "dump", "download all", "print all",
    "who is", "what is the capital", "translate", "define",
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
    temperature=0,          # deterministic — we want consistent SQL, not creative
)

MAX_RETRIES = 2

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace the LLM sometimes adds."""
    raw = re.sub(r"```sql|```", "", raw, flags=re.IGNORECASE)
    return raw.strip()

def scope_check_node(state: dict) -> dict:
    """Gate node — blocks out-of-scope questions before any SQL generation."""
    if not is_in_scope(state["question"]):
        return {**state, "scope_blocked": True}
    return {**state, "scope_blocked": False}


# ── Node 1: Generate SQL ───────────────────────────────────────────────────────

def generate_sql(state: dict) -> dict:
    """
    Ask Claude to generate SQL for the user's question.
    On retries, include the previous error so the LLM can self-correct.
    """
    question   = state["question"]
    retry = state.get("retry_count", 0)  # already incremented by router    
    prev_error = state.get("error", "")

    # On retry, append the error as feedback so LLM knows what went wrong
    prompt = SQL_GENERATION_PROMPT.format(question=question)
    if retry > 0 and prev_error:
        prompt += f"\n\nYour previous attempt failed with this error:\n{prev_error}\nPlease fix the SQL."

    response = llm.invoke([HumanMessage(content=prompt)])
    sql = clean_sql(response.content)

    print(f"\n[generate_sql] attempt {retry + 1}\n{sql}")

    return {**state, "sql": sql, "retry_count": retry}


# ── Node 2: Validate SQL ───────────────────────────────────────────────────────

def validate_node(state: dict) -> dict:
    """
    Run safety + syntax checks. Sets 'valid' flag for the graph router.
    """
    sql = state.get("sql", "")
    valid, message = validate_sql(sql)

    print(f"[validate_sql] valid={valid} | {message}")

    return {**state, "valid": valid, "error": message if not valid else ""}


# ── Node 3: Execute SQL ────────────────────────────────────────────────────────

def execute_node(state: dict) -> dict:
    """
    Run the validated SQL against hotel_bookings.db.
    Sets 'execution_failed' flag so the graph router can direct to fail_node.
    """
    sql = state.get("sql", "")
    ok, result = execute_sql(sql)

    print(f"[execute_sql] ok={ok}")

    if not ok:
        # DB error — do NOT retry (SQL was syntactically valid but failed at runtime)
        # Route directly to fail_node with a clear message
        return {**state, "execution_failed": True, "error": result, "results": ""}

    return {**state, "execution_failed": False, "results": result}


# ── Node 4: Synthesize answer ─────────────────────────────────────────────────

def synthesize(state: dict) -> dict:
    """
    Ask Claude to turn raw SQL results into a plain-English answer.
    """
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


# ── Router — decides what happens after execution ────────────────────────────

def route_after_execution(state: dict) -> str:
    """
    Called by LangGraph after execute_node.
      - "synthesize" → query ran fine, narrate the result
      - "fail"       → runtime DB error, show friendly message
    """
    if state.get("execution_failed"):
        return "fail"
    return "synthesize"


# ── Router — decides what happens after validation ────────────────────────────

def route_after_validation(state: dict) -> str:
    if state.get("valid"):
        return "execute"

    retry = state.get("retry_count", 0) + 1
    if retry >= MAX_RETRIES:
        return "fail"

    state["retry_count"] = retry
    return "retry"

def route_after_scope(state: dict) -> str:
    if state.get("scope_blocked"):
        return "fail"
    return "generate"