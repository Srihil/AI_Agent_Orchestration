from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.models.workflow import AgentExecution, WorkflowRun
from app.schemas.workflow import AgentStatsOut
from app.services.auth_service import get_current_user
from app.tools.registry import AGENT_TOOLS

router = APIRouter(prefix="/agents", tags=["agents"])

AGENT_DESCRIPTIONS = {
    "supervisor": "Orchestrates the workflow by routing tasks to specialized agents, handling failures, and coordinating the overall execution.",
    "researcher": "Gathers information using search tools, web queries, and date/time utilities to provide factual research results.",
    "analyst": "Analyzes information from the researcher to identify patterns, trends, and key insights using structured reasoning.",
    "writer": "Converts research and analysis into coherent, well-structured final responses tailored to the user's request.",
    "reviewer": "Quality-checks the writer's output for accuracy, completeness, and alignment with the original request.",
}


@router.get("", response_model=list[AgentStatsOut])
async def list_agents(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agents = []
    for agent_name, description in AGENT_DESCRIPTIONS.items():
        tools = [t.name for t in AGENT_TOOLS.get(agent_name, [])]

        # Get real execution stats from DB
        total = await session.scalar(
            select(func.count()).select_from(AgentExecution)
            .join(WorkflowRun, AgentExecution.workflow_run_id == WorkflowRun.id)
            .where(WorkflowRun.user_id == current_user.id, AgentExecution.agent_name == agent_name)
        ) or 0

        successful = await session.scalar(
            select(func.count()).select_from(AgentExecution)
            .join(WorkflowRun, AgentExecution.workflow_run_id == WorkflowRun.id)
            .where(WorkflowRun.user_id == current_user.id, AgentExecution.agent_name == agent_name, AgentExecution.status == "success")
        ) or 0

        failed = await session.scalar(
            select(func.count()).select_from(AgentExecution)
            .join(WorkflowRun, AgentExecution.workflow_run_id == WorkflowRun.id)
            .where(WorkflowRun.user_id == current_user.id, AgentExecution.agent_name == agent_name, AgentExecution.status == "failed")
        ) or 0

        avg_duration = await session.scalar(
            select(func.avg(
                func.extract("epoch", AgentExecution.completed_at) -
                func.extract("epoch", AgentExecution.started_at)
            ) * 1000).select_from(AgentExecution)
            .join(WorkflowRun, AgentExecution.workflow_run_id == WorkflowRun.id)
            .where(
                WorkflowRun.user_id == current_user.id,
                AgentExecution.agent_name == agent_name,
                AgentExecution.completed_at.isnot(None),
            )
        )

        agents.append(AgentStatsOut(
            agent_name=agent_name,
            description=description,
            tools=tools,
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            success_rate=round((successful / total * 100) if total else 0, 1),
            avg_duration_ms=round(avg_duration, 1) if avg_duration else None,
        ))

    return agents
