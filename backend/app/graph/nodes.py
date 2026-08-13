"""
Thin wrappers around agent functions that add persistence (event logging, execution tracking).
Each wrapper records start/end events to the database without polluting the agent logic.
"""
import time
import uuid
import logging
from datetime import datetime, timezone
from langgraph.errors import GraphInterrupt
from app.graph.state import WorkflowState
from app.agents.supervisor import supervisor_node
from app.agents.researcher import researcher_node
from app.agents.analyst import analyst_node
from app.agents.writer import writer_node
from app.agents.reviewer import reviewer_node
from app.agents.approval import approval_node
from app.agents.finalize import finalize_node, failed_node

logger = logging.getLogger(__name__)


async def _persist_event(state: WorkflowState, agent_name: str, action: str, status: str,
                          duration_ms: int = None, result_summary: str = None, error: str = None):
    """Write a workflow event to the database."""
    try:
        from app.database.session import AsyncSessionLocal
        from app.models.workflow import WorkflowEvent, WorkflowRun
        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            event = WorkflowEvent(
                id=str(uuid.uuid4()),
                workflow_run_id=state["workflow_run_id"],
                timestamp=datetime.now(timezone.utc),
                agent_name=agent_name,
                action=action,
                status=status,
                duration_ms=duration_ms,
                result_summary=result_summary,
                error=error,
            )
            session.add(event)

            # Update workflow_run current_agent — only update status for running/complete transitions
            run_status = "running"
            if status in ("completed", "failed"):
                run_status = status

            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == state["workflow_run_id"],
                       WorkflowRun.status != "paused")  # never overwrite "paused"
                .values(
                    current_agent=agent_name,
                    status=run_status,
                    step_count=state.get("step_count", 0),
                )
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist event for {agent_name}: {e}")


async def _record_agent_execution(workflow_run_id: str, agent_name: str, started_at: datetime,
                                    status: str, duration_ms: int = None, error: str = None,
                                    tool_calls_count: int = 0):
    """Write a row to agent_executions for real stats on the Agents page."""
    try:
        from app.database.session import AsyncSessionLocal
        from app.models.workflow import AgentExecution
        completed_at = datetime.now(timezone.utc) if status != "running" else None
        async with AsyncSessionLocal() as session:
            exec_row = AgentExecution(
                id=str(uuid.uuid4()),
                workflow_run_id=workflow_run_id,
                agent_name=agent_name,
                started_at=started_at,
                completed_at=completed_at,
                status=status,
                tool_calls_count=tool_calls_count,
                error=error,
            )
            session.add(exec_row)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to record agent execution for {agent_name}: {e}")


def _make_node_wrapper(agent_func, agent_name: str):
    async def wrapper(state: WorkflowState) -> dict:
        start_time = time.monotonic()
        started_at = datetime.now(timezone.utc)
        await _persist_event(state, agent_name, f"{agent_name}_start", "running")

        try:
            result = await agent_func(state)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            has_error = bool(result.get("errors") and len(result["errors"]) > len(state.get("errors", [])))
            event_status = "failed" if has_error else "success"

            summary = None
            if agent_name == "supervisor":
                summary = f"Routing to: {result.get('next_agent', 'unknown')}"
            elif agent_name == "researcher":
                r = result.get("research_results", {})
                summary = r.get("summary", "")[:200] if r else ""
            elif agent_name == "analyst":
                a = result.get("analysis_results", {})
                summary = a.get("summary", "")[:200] if a else ""
            elif agent_name == "writer":
                draft = result.get("draft", "")
                summary = f"Draft produced ({len(draft)} chars)" if draft else ""
            elif agent_name == "reviewer":
                rv = result.get("review_result", {})
                summary = f"{rv.get('status', '?').upper()}: {rv.get('recommendation', '')[:100]}" if rv else ""
            elif agent_name == "approval":
                summary = f"Decision: {result.get('approval_status', 'unknown')}"
            elif agent_name == "finalize":
                fr = result.get("final_response", "")
                summary = f"Final response ({len(fr)} chars)"
            elif agent_name == "failed":
                summary = result.get("final_response", "")[:200]

            await _persist_event(state, agent_name, f"{agent_name}_complete", event_status,
                                  duration_ms=duration_ms, result_summary=summary)

            # Track in agent_executions for the Agents stats page
            tool_calls = len(result.get("tool_results", [])) - len(state.get("tool_results", []))
            await _record_agent_execution(
                state["workflow_run_id"], agent_name, started_at,
                status="success" if event_status == "success" else "failed",
                duration_ms=duration_ms, tool_calls_count=max(0, tool_calls),
            )

            # If finalize/failed, update workflow_run final status
            if agent_name in ("finalize", "failed"):
                try:
                    from app.database.session import AsyncSessionLocal
                    from app.models.workflow import WorkflowRun
                    from sqlalchemy import update

                    final_status = "completed" if agent_name == "finalize" else "failed"
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(WorkflowRun)
                            .where(WorkflowRun.id == state["workflow_run_id"])
                            .values(
                                status=final_status,
                                completed_at=datetime.now(timezone.utc),
                                final_response=result.get("final_response"),
                                current_agent=agent_name,
                            )
                        )
                        await session.commit()
                except Exception as e:
                    logger.warning(f"Failed to update final workflow status: {e}")

            # If approval node paused, update status to paused
            if agent_name == "approval":
                try:
                    from app.database.session import AsyncSessionLocal
                    from app.models.workflow import WorkflowRun
                    from sqlalchemy import update

                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(WorkflowRun)
                            .where(WorkflowRun.id == state["workflow_run_id"])
                            .values(status="paused")
                        )
                        await session.commit()
                except Exception as e:
                    logger.warning(f"Failed to update approval status: {e}")

            return result

        except GraphInterrupt:
            # Not an error — genuine pause for human-in-the-loop.
            duration_ms = int((time.monotonic() - start_time) * 1000)
            # Write the event but DO NOT call _persist_event (it resets status to "running")
            try:
                from app.database.session import AsyncSessionLocal
                from app.models.workflow import WorkflowEvent, WorkflowRun
                from sqlalchemy import update
                import uuid as _uuid
                async with AsyncSessionLocal() as _s:
                    _s.add(WorkflowEvent(
                        id=str(_uuid.uuid4()),
                        workflow_run_id=state["workflow_run_id"],
                        timestamp=datetime.now(timezone.utc),
                        agent_name=agent_name,
                        action=f"{agent_name}_paused",
                        status="success",
                        duration_ms=duration_ms,
                        result_summary="Workflow paused — awaiting human approval",
                    ))
                    # Ensure status stays "paused"
                    await _s.execute(
                        update(WorkflowRun)
                        .where(WorkflowRun.id == state["workflow_run_id"])
                        .values(status="paused", current_agent=agent_name)
                    )
                    await _s.commit()
            except Exception as _e:
                logger.warning(f"Failed to persist paused event: {_e}")
            raise  # must re-raise so LangGraph persists the checkpoint

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _persist_event(state, agent_name, f"{agent_name}_error", "failed",
                                  duration_ms=duration_ms, error=str(e))
            await _record_agent_execution(
                state["workflow_run_id"], agent_name, started_at,
                status="failed", duration_ms=duration_ms, error=str(e),
            )
            raise

    wrapper.__name__ = f"{agent_name}_node_with_persistence"
    return wrapper


supervisor_node_with_persistence = _make_node_wrapper(supervisor_node, "supervisor")
researcher_node_with_persistence = _make_node_wrapper(researcher_node, "researcher")
analyst_node_with_persistence = _make_node_wrapper(analyst_node, "analyst")
writer_node_with_persistence = _make_node_wrapper(writer_node, "writer")
reviewer_node_with_persistence = _make_node_wrapper(reviewer_node, "reviewer")
approval_node_with_persistence = _make_node_wrapper(approval_node, "approval")
finalize_node_with_persistence = _make_node_wrapper(finalize_node, "finalize")
failed_node_with_persistence = _make_node_wrapper(failed_node, "failed")
