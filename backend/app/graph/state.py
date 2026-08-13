from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ResearchResult(TypedDict):
    summary: str
    findings: list[str]
    sources: list[str]
    confidence: float


class AnalysisResult(TypedDict):
    summary: str
    key_points: list[str]
    patterns: list[str]
    conclusion: str


class ReviewResult(TypedDict):
    status: str          # "pass" or "fail"
    issues: list[str]
    missing_information: list[str]
    recommendation: str


class ErrorRecord(TypedDict):
    agent: str
    error: str
    timestamp: str
    retry_count: int


class ToolResult(TypedDict):
    tool_name: str
    input: str
    output: str
    success: bool
    agent: str


class WorkflowState(TypedDict):
    # Identity
    thread_id: str
    user_id: str
    workflow_run_id: str

    # Task
    user_request: str
    current_agent: str
    workflow_status: str          # pending|running|paused|completed|failed

    # Conversation history
    messages: Annotated[list[BaseMessage], add_messages]

    # Agent outputs
    memory_context: Optional[str]
    research_results: Optional[ResearchResult]
    analysis_results: Optional[AnalysisResult]
    draft: Optional[str]
    review_result: Optional[ReviewResult]
    final_response: Optional[str]

    # Tracking
    tool_results: list[ToolResult]
    errors: list[ErrorRecord]

    # Human-in-the-loop
    approval_status: Optional[str]   # pending|approved|rejected
    require_approval: bool

    # Control flow guards
    step_count: int
    max_steps: int
    review_cycles: int
    max_review_cycles: int
    retry_counts: dict[str, int]
    max_retries: int

    # Routing decision from supervisor
    next_agent: Optional[str]        # researcher|analyst|writer|reviewer|approval|end|failed
