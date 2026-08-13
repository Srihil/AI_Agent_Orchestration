import json
import re
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage
from app.config.prompts import SUPERVISOR_SYSTEM
from app.graph.state import WorkflowState
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Extract JSON object from model output, handling markdown fences and prose."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return part.split("```")[0].strip()
    # Try to find raw JSON object
    match = re.search(r'\{[^{}]*"next_agent"[^{}]*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    # Return as-is and let json.loads raise the error
    return text


def _build_supervisor_context(state: WorkflowState) -> str:
    parts = [f"User Request: {state['user_request']}"]
    parts.append(f"Step: {state['step_count']}/{state['max_steps']}")
    parts.append(f"Review cycles: {state['review_cycles']}/{state['max_review_cycles']}")
    parts.append(f"Require approval: {state['require_approval']}")

    if state.get("memory_context"):
        parts.append(f"\nMemory context:\n{state['memory_context']}")

    if state.get("research_results"):
        r = state["research_results"]
        parts.append(f"\nResearch done — confidence: {r.get('confidence', '?')}")
        parts.append(f"Summary: {r.get('summary', '')[:200]}")
    else:
        parts.append("\nResearch: not yet done")

    if state.get("analysis_results"):
        a = state["analysis_results"]
        parts.append(f"\nAnalysis done — conclusion: {a.get('conclusion', '')[:200]}")
    else:
        parts.append("\nAnalysis: not yet done")

    if state.get("draft"):
        parts.append(f"\nDraft exists ({len(state['draft'])} chars)")
    else:
        parts.append("\nDraft: not yet written")

    if state.get("review_result"):
        rv = state["review_result"]
        parts.append(f"\nReview result: {rv.get('status', '?').upper()}")
        if rv.get("issues"):
            parts.append(f"Issues: {', '.join(rv['issues'][:3])}")
    else:
        parts.append("\nReview: not yet done")

    if state.get("errors"):
        recent = state["errors"][-3:]
        parts.append(f"\nRecent errors: {json.dumps(recent)}")

    if state.get("approval_status"):
        parts.append(f"\nApproval status: {state['approval_status']}")

    return "\n".join(parts)


async def supervisor_node(state: WorkflowState) -> dict:
    llm = get_llm(temperature=0.0)
    context = _build_supervisor_context(state)

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM),
        HumanMessage(content=f"Current workflow state:\n\n{context}\n\nWhat should happen next? Respond with JSON only."),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Robustly extract JSON from model output (handles markdown, prose, etc.)
        content = _extract_json(content)
        decision = json.loads(content)
        next_agent = decision.get("next_agent", "end")
        reasoning = decision.get("reasoning", "")
        instructions = decision.get("instructions", "")

        valid_agents = {"researcher", "analyst", "writer", "reviewer", "approval", "end", "failed"}
        if next_agent not in valid_agents:
            logger.warning(f"Supervisor returned invalid next_agent: {next_agent}, defaulting to end")
            next_agent = "end"

        logger.info(f"Supervisor decision: {next_agent} — {reasoning}")

        new_step_count = state["step_count"] + 1
        if new_step_count >= state["max_steps"] and next_agent not in {"end", "failed"}:
            logger.warning(f"Max steps ({state['max_steps']}) reached, forcing end")
            next_agent = "end"
            instructions = "Max steps reached. Use whatever final_response is available."

        return {
            "next_agent": next_agent,
            "current_agent": "supervisor",
            "step_count": new_step_count,
            "messages": [HumanMessage(content=f"[Supervisor] Routing to {next_agent}: {reasoning}")],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Supervisor returned invalid JSON: {e}")
        errors = list(state.get("errors", []))
        errors.append({
            "agent": "supervisor",
            "error": f"Invalid JSON response: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        })
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts["supervisor"] = retry_counts.get("supervisor", 0) + 1

        if retry_counts["supervisor"] >= state.get("max_retries", 3):
            return {"next_agent": "end", "errors": errors, "retry_counts": retry_counts}

        return {
            "next_agent": "end",
            "errors": errors,
            "retry_counts": retry_counts,
            "step_count": state["step_count"] + 1,
        }

    except Exception as e:
        logger.error(f"Supervisor node failed: {e}")
        errors = list(state.get("errors", []))
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts["supervisor"] = retry_counts.get("supervisor", 0) + 1
        errors.append({
            "agent": "supervisor",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_counts["supervisor"],
        })
        # Only route to failed after exhausting retries — not on first error
        if retry_counts["supervisor"] >= state.get("max_retries", 3):
            return {
                "next_agent": "failed",
                "errors": errors,
                "retry_counts": retry_counts,
                "step_count": state["step_count"] + 1,
            }
        # Re-enter supervisor to retry
        return {
            "next_agent": "researcher",  # safe default: start with research
            "errors": errors,
            "retry_counts": retry_counts,
            "step_count": state["step_count"] + 1,
            "messages": [HumanMessage(content=f"[Supervisor] Error, retrying ({retry_counts['supervisor']}): {str(e)[:100]}")],
        }
