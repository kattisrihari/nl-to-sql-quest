"""
graph.py — Wires all nodes into a LangGraph StateGraph.

Flow:
  generate_sql → validate → [retry loop or execute] → synthesize → END
                                    ↑_______________|
"""

from langgraph.graph import StateGraph, END
# Add route_after_execution to the import
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

# ── State schema ───────────────────────────────────────────────────────────────
# All keys that flow through the graph
def get_initial_state(question: str) -> dict:
    return {
        "question":    question,
        "sql":         "",
        "valid":       False,
        "error":       "",
        "results":     "",
        "answer":      "",
        "retry_count": 0,
    }


# ── Build graph ────────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(dict)

    # Register nodes
    graph.add_node("generate",   generate_sql)
    graph.add_node("validate",   validate_node)
    graph.add_node("execute",    execute_node)
    graph.add_node("synthesize", synthesize)
    graph.add_node("fail",       fail_node)


        # Register
    graph.add_node("scope_check", scope_check_node)

    # Entry point changes
    graph.set_entry_point("scope_check")

    # Add edges
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges(
        "scope_check",
        route_after_scope,
        {"generate": "generate", "fail": "fail"}
    )

    graph.add_edge("synthesize", END)
    graph.add_edge("fail",       END)

    # Replace with this:
    graph.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "synthesize": "synthesize",
            "fail":       "fail",
        }
        )
    # Conditional edge — router decides after validation
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "execute": "execute",
            "retry":   "generate",   # loops back with error feedback
            "fail":    "fail",
        }
    )

    return graph.compile()


# ── Convenience runner ─────────────────────────────────────────────────────────
def run_query(question: str) -> str:
    """Run a natural language question through the full agent pipeline."""
    agent = build_graph()
    state = get_initial_state(question)
    result = agent.invoke(state)
    return result.get("answer", "No answer generated.")


# ── Smoke test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    q = "How many bookings did we receive from each region during August 2026?"
    print(f"\nQuestion: {q}")
    print(f"\nAnswer: {run_query(q)}")
