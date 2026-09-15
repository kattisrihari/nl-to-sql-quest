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
    total_rows: int | None = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def run_query(request: QueryRequest):
    try:
        state = get_initial_state(request.query)
        result = agent.invoke(state)

        if not result or not isinstance(result, dict):
            return QueryResponse(summary="Could not process that question.")

        sql = result.get("sql", None)
        raw_data = []

        if sql and not result.get("scope_blocked") and not result.get("execution_failed"):
            ok, rows, err = execute_sql_raw(sql)
            print(f"[api] execute_sql_raw ok={ok} rows={len(rows)} err={err}")  # ← add this
            if ok:
                raw_data = rows

        total_rows = len(raw_data)
        display_data = raw_data[:50] if total_rows > 50 else raw_data

        return QueryResponse(
            summary=result.get("answer", "No answer generated."),
            sql_query=sql or None,
            data=display_data or None,
            total_rows=total_rows if total_rows > 0 else None,
        )

    except Exception as e:
        print(f"[api] ERROR: {e}")  # ← add this
        import traceback; traceback.print_exc()  # ← add this
        return QueryResponse(summary="An error occurred processing your request. Please try again.")