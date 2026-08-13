from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.models.workflow import WorkflowRun, WorkflowEvent
from app.schemas.workflow import WorkflowCreate, WorkflowOut, WorkflowDetailOut, WorkflowEventOut, MetricsOut
from app.services.auth_service import get_current_user
from app.services.workflow_service import (
    create_workflow, run_workflow, get_workflow_state, get_workflow_metrics
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowOut, status_code=201)
async def create_workflow_endpoint(
    body: WorkflowCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await create_workflow(
        session=session,
        user_id=current_user.id,
        task=body.task,
        require_approval=body.require_approval,
        max_steps=body.max_steps,
    )
    background_tasks.add_task(run_workflow, run.id, current_user.id)
    return run


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    result = await session.execute(
        select(WorkflowRun)
        .where(WorkflowRun.user_id == current_user.id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/metrics", response_model=MetricsOut)
async def workflow_metrics(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_workflow_metrics(session, current_user.id)


@router.get("/{workflow_id}", response_model=WorkflowDetailOut)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(WorkflowRun).where(
            WorkflowRun.id == workflow_id,
            WorkflowRun.user_id == current_user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")

    events_result = await session.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_run_id == workflow_id)
        .order_by(WorkflowEvent.timestamp)
    )
    events = events_result.scalars().all()

    return {
        **WorkflowOut.model_validate(run).model_dump(),
        "events": [WorkflowEventOut.model_validate(e).model_dump() for e in events],
    }


@router.get("/{workflow_id}/events", response_model=list[WorkflowEventOut])
async def get_workflow_events(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await session.get(WorkflowRun, workflow_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    result = await session.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_run_id == workflow_id)
        .order_by(WorkflowEvent.timestamp)
    )
    return result.scalars().all()


@router.get("/{workflow_id}/state")
async def get_workflow_graph_state(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await session.get(WorkflowRun, workflow_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    state = await get_workflow_state(run.thread_id)
    if not state:
        return {"message": "No graph state available yet"}

    # Return safe subset of state (no raw message objects)
    return {
        "current_agent": state.get("current_agent"),
        "workflow_status": state.get("workflow_status"),
        "step_count": state.get("step_count"),
        "next_agent": state.get("next_agent"),
        "has_research": state.get("research_results") is not None,
        "has_analysis": state.get("analysis_results") is not None,
        "has_draft": state.get("draft") is not None,
        "review_status": state.get("review_result", {}).get("status") if state.get("review_result") else None,
        "approval_status": state.get("approval_status"),
        "errors_count": len(state.get("errors", [])),
    }


@router.delete("/{workflow_id}", status_code=204)
async def cancel_or_delete_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await session.get(WorkflowRun, workflow_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if run.status in ("running", "pending", "awaiting_approval"):
        # Cancel in-progress run; background task is still active so don't delete the row
        await session.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == workflow_id)
            .values(status="failed", error_message="Cancelled by user")
        )
        await session.commit()
    else:
        # Permanently remove completed/failed records and all cascaded children
        await session.delete(run)
        await session.commit()
