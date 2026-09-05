"""
api.py — FastAPI server that wraps the LangGraph NL2SQL agent.

Runs at: http://127.0.0.1:8000
Docs at: http://127.0.0.1:8000/docs

Usage:
    uvicorn api:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from src.agent.graph import build_graph, get_initial_state
from src.agent.tools import execute_sql_raw

app = FastAPI(title="Hotel Bookings NL2SQL API")

# ── CORS — allow React dev server to call this API ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Compile graph once at startup (not per request) ───────────────────────────
agent = build_graph()


# ── Request / Response models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    summary: str
    sql_query: str | None = None
    data: list[dict[str, Any]] | None = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def run_query(request: QueryRequest):
    """
    Accepts a natural language question, runs the full LangGraph agent,
    and returns the AI summary, generated SQL, and raw data rows.
    """
    state = get_initial_state(request.query)
    result = agent.invoke(state)

    summary   = result.get("answer", "No answer generated.")
    sql       = result.get("sql", None)
    raw_data  = []

    # Fetch raw rows for the data table in the UI
    # Only if SQL was generated and execution succeeded
    if sql and not result.get("scope_blocked") and not result.get("execution_failed"):
        ok, rows, _ = execute_sql_raw(sql)
        if ok:
            raw_data = rows

    return QueryResponse(
        summary=summary,
        sql_query=sql if sql else None,
        data=raw_data if raw_data else None,
    )