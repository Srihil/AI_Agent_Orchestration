"""
Central workflow service: creates, runs, resumes, and queries workflow state.
Workflows execute as FastAPI BackgroundTasks — async but non-blocking for HTTP.
"""
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.config.settings import settings
from app.graph.state import WorkflowState
from app.models.workflow import WorkflowRun, WorkflowEvent, AgentExecution
from app.models.approval import Approval
from app.memory.manager import get_relevant_memories
from app.tools.memory_search import set_memory_context

logger = logging.getLogger(__name__)

# Global compiled graph (initialized at startup)
_compiled_graph = None
_checkpointer = None


async def init_graph():
    """Initialize the LangGraph compiled graph with PostgreSQL checkpointer."""
    global _compiled_graph, _checkpointer, _pool
    from app.graph.workflow import build_graph
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    graph = build_graph()
    conn_str = settings.LANGGRAPH_DATABASE_URL  # raw psycopg URL, no +driver prefix

    # AsyncConnectionPool with autocommit=True required for LangGraph's
    # CREATE INDEX CONCURRENTLY statements during setup()
    pool = AsyncConnectionPool(
        conninfo=conn_str,
        max_size=5,
        open=False,
        kwargs={"autocommit": True},
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    # No interrupt_before — the approval_node calls interrupt() itself AFTER saving
    # the Approval DB record. This lets the node persist the approval before pausing.
    _compiled_graph = graph.compile(checkpointer=checkpointer)
    _checkpointer = checkpointer
    _pool = pool
    logger.info("LangGraph initialized with PostgreSQL checkpointer")


_pool = None


async def shutdown_graph():
    global _checkpointer, _pool
    if _pool:
        try:
            await _pool.close()
        except Exception as e:
            logger.warning(f"Graph pool shutdown error: {e}")


def get_compiled_graph():
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph() first.")
    return _compiled_graph


async def create_workflow(
    session: AsyncSession,
    user_id: str,
    task: str,
    require_approval: bool = False,
    max_steps: int = None,
) -> WorkflowRun:
    thread_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    effective_max_steps = max_steps or settings.MAX_WORKFLOW_STEPS

    run = WorkflowRun(
        id=run_id,
        user_id=user_id,
        thread_id=thread_id,
        task=task,
        status="pending",
        max_steps=effective_max_steps,
        require_approval=require_approval,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def run_workflow(workflow_run_id: str, user_id: str) -> None:
    """
    Execute the workflow. Called as a BackgroundTask.
    Streams LangGraph events and persists state continuously to PostgreSQL.
    """
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            logger.error(f"WorkflowRun {workflow_run_id} not found")
            return

        # Fetch relevant memories
        memory_context = await get_relevant_memories(session, user_id, run.task)

    # Set memory context for in-process tool calls
    set_memory_context(user_id)

    graph = get_compiled_graph()
    thread_id = run.thread_id

    initial_state: WorkflowState = {
        "thread_id": thread_id,
        "user_id": user_id,
        "workflow_run_id": workflow_run_id,
        "user_request": run.task,
        "current_agent": "supervisor",
        "workflow_status": "running",
        "messages": [HumanMessage(content=run.task)],
        "memory_context": memory_context or None,
        "research_results": None,
        "analysis_results": None,
        "draft": None,
        "review_result": None,
        "final_response": None,
        "tool_results": [],
        "errors": [],
        "approval_status": None,
        "require_approval": run.require_approval,
        "step_count": 0,
        "max_steps": run.max_steps,
        "review_cycles": 0,
        "max_review_cycles": settings.MAX_REVIEW_CYCLES,
        "retry_counts": {},
        "max_retries": settings.MAX_RETRIES,
        "next_agent": None,
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Update status to running
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == workflow_run_id)
                .values(status="running", started_at=datetime.now(timezone.utc))
            )
            await session.commit()

        # Run the graph — streams events automatically to checkpointer
        async for event in graph.astream(initial_state, config=config, stream_mode="values"):
            workflow_status = event.get("workflow_status", "running")
            if workflow_status in ("completed", "failed"):
                break

        logger.info(f"Workflow {thread_id} graph execution ended (may be paused for approval)")

    except Exception as e:
        # Check if this is an interrupt (pause for human approval) — not a real failure
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            logger.info(f"Workflow {thread_id} paused for human approval")
            # Status already set to "paused" inside approval_node — nothing more to do
            return

        logger.error(f"Workflow {thread_id} execution error: {e}", exc_info=True)
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == workflow_run_id)
                .values(
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(e),
                )
            )
            await session.commit()


async def resume_workflow(thread_id: str, decision: str) -> None:
    """
    Resume a paused workflow after a human approval decision.
    Uses LangGraph's Command(resume=...) mechanism.
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        from app.database.session import AsyncSessionLocal

        # Mark workflow as running again before resuming
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.thread_id == thread_id)
                .values(status="running")
            )
            await session.commit()

        # Resume the graph — approval_node will update the Approval record after interrupt resumes
        resume_value = {"decision": decision}
        async for event in graph.astream(
            Command(resume=resume_value),
            config=config,
            stream_mode="values",
        ):
            workflow_status = event.get("workflow_status", "running")
            if workflow_status in ("completed", "failed"):
                break

        logger.info(f"Workflow {thread_id} resumed with decision: {decision}")

    except Exception as e:
        logger.error(f"Resume workflow {thread_id} failed: {e}", exc_info=True)
        from app.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.thread_id == thread_id)
                .values(status="failed", error_message=f"Resume failed: {str(e)}")
            )
            await session.commit()


async def get_workflow_state(thread_id: str) -> dict | None:
    """Get the current LangGraph checkpoint state for a thread."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await graph.aget_state(config)
        if state and state.values:
            return dict(state.values)
    except Exception as e:
        logger.warning(f"Could not get graph state for {thread_id}: {e}")
    return None


async def get_workflow_metrics(session: AsyncSession, user_id: str) -> dict:
    """Calculate real metrics from database records."""
    from sqlalchemy import func

    total = await session.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.user_id == user_id))
    completed = await session.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.user_id == user_id, WorkflowRun.status == "completed"))
    failed = await session.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.user_id == user_id, WorkflowRun.status == "failed"))
    running = await session.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.user_id == user_id, WorkflowRun.status == "running"))
    paused = await session.scalar(select(func.count()).select_from(WorkflowRun).where(WorkflowRun.user_id == user_id, WorkflowRun.status == "paused"))
    pending_approvals = await session.scalar(
        select(func.count()).select_from(Approval)
        .join(WorkflowRun, Approval.workflow_run_id == WorkflowRun.id)
        .where(WorkflowRun.user_id == user_id, Approval.status == "pending")
    )

    # Average duration for completed workflows
    from sqlalchemy import case
    avg_duration_row = await session.execute(
        select(
            func.avg(
                func.extract("epoch", WorkflowRun.completed_at) -
                func.extract("epoch", WorkflowRun.started_at)
            )
        ).where(
            WorkflowRun.user_id == user_id,
            WorkflowRun.status == "completed",
            WorkflowRun.completed_at.isnot(None),
        )
    )
    avg_duration = avg_duration_row.scalar()

    return {
        "total": total or 0,
        "completed": completed or 0,
        "failed": failed or 0,
        "running": running or 0,
        "paused": paused or 0,
        "pending_approvals": pending_approvals or 0,
        "success_rate": round((completed / total * 100) if total else 0, 1),
        "avg_duration_seconds": round(avg_duration or 0, 1),
    }
