import uuid
import logging
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
from app.graph.state import WorkflowState

logger = logging.getLogger(__name__)


async def approval_node(state: WorkflowState) -> dict:
    """
    Human-in-the-loop node. Persists an Approval record to the DB BEFORE
    calling interrupt(), so the frontend can display and act on it.
    Execution resumes when Command(resume={"decision": "approved"|"rejected"})
    is called from the approvals API.
    """
    draft = state.get("draft", "")
    research = state.get("research_results") or {}
    approval_id = str(uuid.uuid4())

    # Persist the approval request BEFORE interrupting so the API can find it
    await _save_approval(
        approval_id=approval_id,
        workflow_run_id=state["workflow_run_id"],
        thread_id=state["thread_id"],
        requesting_agent=state.get("current_agent", "supervisor"),
        action_description=f"Deliver final response to: {state['user_request'][:300]}",
        reason=(
            f"Research completed (confidence: {research.get('confidence', 'unknown')}). "
            f"Draft is {len(draft)} characters. Human review requested before delivery."
        ),
        risk_level="medium",
    )

    approval_payload = {
        "approval_id": approval_id,
        "workflow_run_id": state["workflow_run_id"],
        "thread_id": state["thread_id"],
        "requesting_agent": state.get("current_agent", "supervisor"),
        "action_description": f"Deliver final response to: {state['user_request'][:300]}",
        "reason": f"Draft ready ({len(draft)} chars). Awaiting human approval.",
        "draft_preview": draft[:500] if draft else "",
    }

    logger.info(f"Workflow {state['thread_id']} pausing for human approval (approval_id={approval_id})")

    # Genuine pause — LangGraph saves checkpoint to PostgreSQL.
    # Resumes when Command(resume={"decision": "approved"|"rejected"}) is called.
    decision = interrupt(approval_payload)

    # Resumes here after human decision
    decision_value = decision if isinstance(decision, str) else decision.get("decision", "approved")
    logger.info(f"Approval {approval_id} decision: {decision_value}")

    # Update DB record with the decision
    await _update_approval(approval_id, decision_value)

    return {
        "approval_status": decision_value,
        "current_agent": "approval",
        "messages": [HumanMessage(content=f"[Approval] Human decision: {decision_value.upper()}")],
    }


async def _save_approval(approval_id: str, workflow_run_id: str, thread_id: str,
                          requesting_agent: str, action_description: str,
                          reason: str, risk_level: str):
    try:
        from app.database.session import AsyncSessionLocal
        from app.models.approval import Approval
        from sqlalchemy import update
        from app.models.workflow import WorkflowRun

        async with AsyncSessionLocal() as session:
            approval = Approval(
                id=approval_id,
                workflow_run_id=workflow_run_id,
                thread_id=thread_id,
                requesting_agent=requesting_agent,
                action_description=action_description,
                reason=reason,
                risk_level=risk_level,
                status="pending",
            )
            session.add(approval)
            # Mark workflow as paused
            await session.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == workflow_run_id)
                .values(status="paused")
            )
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to save approval record: {e}")


async def _update_approval(approval_id: str, decision: str):
    try:
        from app.database.session import AsyncSessionLocal
        from app.models.approval import Approval

        async with AsyncSessionLocal() as session:
            result = await session.get(Approval, approval_id)
            if result:
                result.status = decision
                result.decided_at = datetime.now(timezone.utc)
                await session.commit()
    except Exception as e:
        logger.warning(f"Failed to update approval {approval_id}: {e}")
