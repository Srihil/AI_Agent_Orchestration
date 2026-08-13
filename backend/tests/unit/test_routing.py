import pytest
from app.graph.workflow import supervisor_router, review_router, approval_router
from app.graph.state import WorkflowState


def make_state(**kwargs) -> WorkflowState:
    defaults = {
        "thread_id": "test",
        "user_id": "user1",
        "workflow_run_id": "run1",
        "user_request": "test task",
        "current_agent": "supervisor",
        "workflow_status": "running",
        "messages": [],
        "memory_context": None,
        "research_results": None,
        "analysis_results": None,
        "draft": None,
        "review_result": None,
        "final_response": None,
        "tool_results": [],
        "errors": [],
        "approval_status": None,
        "require_approval": False,
        "step_count": 0,
        "max_steps": 20,
        "review_cycles": 0,
        "max_review_cycles": 3,
        "retry_counts": {},
        "max_retries": 3,
        "next_agent": None,
    }
    defaults.update(kwargs)
    return defaults


class TestSupervisorRouter:
    def test_routes_to_researcher(self):
        state = make_state(next_agent="researcher")
        assert supervisor_router(state) == "researcher"

    def test_routes_to_analyst(self):
        state = make_state(next_agent="analyst")
        assert supervisor_router(state) == "analyst"

    def test_routes_to_writer(self):
        state = make_state(next_agent="writer")
        assert supervisor_router(state) == "writer"

    def test_routes_to_reviewer(self):
        state = make_state(next_agent="reviewer")
        assert supervisor_router(state) == "reviewer"

    def test_routes_end_to_finalize(self):
        state = make_state(next_agent="end")
        assert supervisor_router(state) == "finalize"

    def test_routes_failed(self):
        state = make_state(next_agent="failed")
        assert supervisor_router(state) == "failed"

    def test_invalid_next_agent_defaults_to_finalize(self):
        state = make_state(next_agent="nonexistent")
        assert supervisor_router(state) == "finalize"

    def test_none_next_agent_defaults_to_finalize(self):
        state = make_state(next_agent=None)
        assert supervisor_router(state) == "finalize"


class TestReviewRouter:
    def test_pass_without_approval_goes_to_finalize(self):
        state = make_state(
            review_result={"status": "pass", "issues": [], "missing_information": [], "recommendation": "good"},
            require_approval=False,
        )
        assert review_router(state) == "finalize"

    def test_pass_with_approval_required_goes_to_approval(self):
        state = make_state(
            review_result={"status": "pass", "issues": [], "missing_information": [], "recommendation": "good"},
            require_approval=True,
            approval_status=None,
        )
        assert review_router(state) == "approval"

    def test_pass_already_approved_goes_to_finalize(self):
        state = make_state(
            review_result={"status": "pass", "issues": [], "missing_information": [], "recommendation": "good"},
            require_approval=True,
            approval_status="approved",
        )
        assert review_router(state) == "finalize"

    def test_fail_goes_to_supervisor(self):
        state = make_state(
            review_result={"status": "fail", "issues": ["missing details"], "missing_information": [], "recommendation": "redo"},
            require_approval=False,
        )
        assert review_router(state) == "supervisor"


class TestApprovalRouter:
    def test_approved_goes_to_finalize(self):
        state = make_state(approval_status="approved")
        assert approval_router(state) == "finalize"

    def test_rejected_goes_to_supervisor(self):
        state = make_state(approval_status="rejected")
        assert approval_router(state) == "supervisor"

    def test_no_status_goes_to_supervisor(self):
        state = make_state(approval_status=None)
        assert approval_router(state) == "supervisor"
