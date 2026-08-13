import logging
from langchain_core.messages import HumanMessage
from app.graph.state import WorkflowState

logger = logging.getLogger(__name__)


async def finalize_node(state: WorkflowState) -> dict:
    draft = state.get("draft", "")
    research = state.get("research_results") or {}
    analysis = state.get("analysis_results") or {}

    if draft:
        final_response = draft
    elif research.get("summary"):
        final_response = f"## Research Summary\n\n{research['summary']}\n\n"
        if research.get("findings"):
            final_response += "### Key Findings\n" + "\n".join(f"- {f}" for f in research["findings"])
    else:
        final_response = "The workflow completed but could not produce a meaningful response."

    logger.info(f"Workflow finalized with {len(final_response)} char response")

    return {
        "final_response": final_response,
        "workflow_status": "completed",
        "current_agent": "finalize",
        "messages": [HumanMessage(content=f"[Finalize] Workflow completed ({len(final_response)} chars)")],
    }


async def failed_node(state: WorkflowState) -> dict:
    errors = state.get("errors", [])
    error_summary = "; ".join(e.get("error", "unknown") for e in errors[-3:]) if errors else "Unknown failure"

    logger.error(f"Workflow {state['thread_id']} failed: {error_summary}")

    return {
        "workflow_status": "failed",
        "current_agent": "failed",
        "final_response": f"The workflow encountered an unrecoverable error: {error_summary}",
        "messages": [HumanMessage(content=f"[Failed] Workflow terminated: {error_summary[:200]}")],
    }
