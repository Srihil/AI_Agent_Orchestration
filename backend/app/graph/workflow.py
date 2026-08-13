from langgraph.graph import StateGraph, START, END
from app.graph.state import WorkflowState
from app.graph.nodes import (
    supervisor_node_with_persistence,
    researcher_node_with_persistence,
    analyst_node_with_persistence,
    writer_node_with_persistence,
    reviewer_node_with_persistence,
    approval_node_with_persistence,
    finalize_node_with_persistence,
    failed_node_with_persistence,
)
# AsyncPostgresSaver is imported lazily in create_graph_with_checkpointer
# to avoid requiring libpq at import time (enables unit testing without DB driver)


def supervisor_router(state: WorkflowState) -> str:
    """Conditional edge: routes from supervisor based on next_agent decision."""
    next_agent = state.get("next_agent", "end")
    valid = {"researcher", "analyst", "writer", "reviewer", "approval", "finalize", "failed"}
    if next_agent == "end":
        return "finalize"
    if next_agent not in valid:
        return "finalize"
    return next_agent


def review_router(state: WorkflowState) -> str:
    """Conditional edge: after review, either finalize or route back via supervisor."""
    review = state.get("review_result", {})
    approval_status = state.get("approval_status")

    # If reviewer passed and no approval needed, finalize
    if review.get("status") == "pass":
        if state.get("require_approval") and approval_status not in ("approved",):
            return "approval"
        return "finalize"

    # Reviewer failed — let supervisor decide next step
    return "supervisor"


def approval_router(state: WorkflowState) -> str:
    """Conditional edge: after human approval decision."""
    status = state.get("approval_status", "rejected")
    if status == "approved":
        return "finalize"
    # Rejected — back to supervisor to decide what to do
    return "supervisor"


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)

    # Register all nodes
    graph.add_node("supervisor", supervisor_node_with_persistence)
    graph.add_node("researcher", researcher_node_with_persistence)
    graph.add_node("analyst", analyst_node_with_persistence)
    graph.add_node("writer", writer_node_with_persistence)
    graph.add_node("reviewer", reviewer_node_with_persistence)
    graph.add_node("approval", approval_node_with_persistence)
    graph.add_node("finalize", finalize_node_with_persistence)
    graph.add_node("failed", failed_node_with_persistence)

    # Entry point
    graph.add_edge(START, "supervisor")

    # Supervisor routes conditionally to any agent
    graph.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "writer": "writer",
            "reviewer": "reviewer",
            "approval": "approval",
            "finalize": "finalize",
            "failed": "failed",
        },
    )

    # Each specialized agent returns to supervisor after completion
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("writer", "supervisor")

    # Reviewer: conditional routing based on pass/fail
    graph.add_conditional_edges(
        "reviewer",
        review_router,
        {
            "supervisor": "supervisor",
            "approval": "approval",
            "finalize": "finalize",
        },
    )

    # Approval: conditional routing based on human decision
    graph.add_conditional_edges(
        "approval",
        approval_router,
        {
            "finalize": "finalize",
            "supervisor": "supervisor",
        },
    )

    # Terminal nodes
    graph.add_edge("finalize", END)
    graph.add_edge("failed", END)

    return graph


async def create_graph_with_checkpointer(db_url: str) -> tuple:
    """Create compiled graph with PostgreSQL checkpointer."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    graph = build_graph()

    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        await checkpointer.setup()

    checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    compiled = graph.compile(checkpointer=checkpointer)

    return compiled, checkpointer
