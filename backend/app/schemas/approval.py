from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ApprovalOut(BaseModel):
    id: str
    workflow_run_id: str
    thread_id: str
    requesting_agent: str
    action_description: str
    reason: str
    risk_level: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime]
    decision_note: Optional[str]

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    decision_note: Optional[str] = None
