import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.models.approval import Approval
from app.models.workflow import WorkflowRun
from app.schemas.approval import ApprovalOut, ApprovalDecision
from app.services.auth_service import get_current_user
from app.services.workflow_service import resume_workflow

router = APIRouter(prefix="/approvals", tags=["approvals"])


async def _get_user_approval(approval_id: str, user_id: str, session: AsyncSession) -> Approval:
    result = await session.execute(
        select(Approval)
        .join(WorkflowRun, Approval.workflow_run_id == WorkflowRun.id)
        .where(Approval.id == approval_id, WorkflowRun.user_id == user_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(
    status: str = "pending",
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Approval)
        .join(WorkflowRun, Approval.workflow_run_id == WorkflowRun.id)
        .where(WorkflowRun.user_id == current_user.id)
        .order_by(Approval.created_at.desc())
    )
    if status != "all":
        stmt = stmt.where(Approval.status == status)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
async def approve(
    approval_id: str,
    body: ApprovalDecision,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = await _get_user_approval(approval_id, current_user.id, session)
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already decided: {approval.status}")

    approval.decision_note = body.decision_note
    await session.commit()

    background_tasks.add_task(resume_workflow, approval.thread_id, "approved")
    await session.refresh(approval)
    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
async def reject(
    approval_id: str,
    body: ApprovalDecision,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = await _get_user_approval(approval_id, current_user.id, session)
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval already decided: {approval.status}")

    approval.decision_note = body.decision_note
    await session.commit()

    background_tasks.add_task(resume_workflow, approval.thread_id, "rejected")
    await session.refresh(approval)
    return approval
