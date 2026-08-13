from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    task: str
    require_approval: bool = False
    max_steps: Optional[int] = None


class WorkflowOut(BaseModel):
    id: str
    thread_id: str
    task: str
    status: str
    current_agent: Optional[str]
    step_count: int
    max_steps: int
    require_approval: bool
    started_at: datetime
    completed_at: Optional[datetime]
    final_response: Optional[str]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class WorkflowEventOut(BaseModel):
    id: str
    timestamp: datetime
    agent_name: Optional[str]
    action: str
    tool_name: Optional[str]
    status: str
    duration_ms: Optional[int]
    result_summary: Optional[str]
    error: Optional[str]

    model_config = {"from_attributes": True}


class WorkflowDetailOut(WorkflowOut):
    events: list[WorkflowEventOut] = []


class AgentStatsOut(BaseModel):
    agent_name: str
    description: str
    tools: list[str]
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_ms: Optional[float]


class MetricsOut(BaseModel):
    total: int
    completed: int
    failed: int
    running: int
    paused: int
    pending_approvals: int
    success_rate: float
    avg_duration_seconds: float
