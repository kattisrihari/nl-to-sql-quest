"""
graph.py — Wires all nodes into a LangGraph StateGraph.

Flow:
  scope_check → generate_sql → validate → [retry loop or execute] → synthesize → END
                                    ↑_______________|
"""

from langgraph.graph import StateGraph, END
from src.agent.nodes import (
    generate_sql,
    validate_node,
    execute_node,
    synthesize,
    fail_node,
    route_after_validation,
    route_after_execution,
    scope_check_node,
    route_after_scope,
)


# ── Initial state ──────────────────────────────────────────────────────────────
def get_initial_state(question: str) -> dict:
    return {
        "question":         question,
        "sql":              "",
        "last_sql":         "",       # tracks previous SQL to detect stuck loops
        "valid":            False,
        "error":            "",
        "results":          "",       # always reset — prevents state leak between queries
        "answer":           "",
        "retry_count":      0,
        "scope_blocked":    False,
        "execution_failed": False,
    }


# ── Build graph ────────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(dict)

    # Register nodes
    graph.add_node("scope_check", scope_check_node)
    graph.add_node("generate",    generate_sql)
    graph.add_node("validate",    validate_node)
    graph.add_node("execute",     execute_node)
    graph.add_node("synthesize",  synthesize)
    graph.add_node("fail",        fail_node)

    # Entry point
    graph.set_entry_point("scope_check")

    # Fixed edges
    graph.add_edge("generate",   "validate")
    graph.add_edge("synthesize", END)
    graph.add_edge("fail",       END)

    # Conditional: scope check
    graph.add_conditional_edges(
        "scope_check",
        route_after_scope,
        {"generate": "generate", "fail": "fail"}
    )

    # Conditional: after execution
    graph.add_conditional_edges(
        "execute",
        route_after_execution,
        {"synthesize": "synthesize", "fail": "fail"}
    )

    # Conditional: after validation (retry loop)
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {"execute": "execute", "retry": "generate", "fail": "fail"}
    )

    return graph.compile()


# ── Convenience runners ────────────────────────────────────────────────────────
def run_query(question: str) -> str:
    """Returns just the answer string — used by CLI app."""
    agent = build_graph()
    state = get_initial_state(question)
    result = agent.invoke(state)
    return result.get("answer", "No answer generated.")


def run_query_full(question: str) -> dict:
    """Returns full state dict — used by FastAPI."""
    agent = build_graph()
    state = get_initial_state(question)
    return agent.invoke(state)


# ── Smoke test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    q = "How many bookings did we receive from each region during August 2026?"
    print(f"\nQuestion: {q}")
    print(f"\nAnswer: {run_query(q)}")