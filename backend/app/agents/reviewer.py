import json
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage
from app.config.prompts import REVIEWER_SYSTEM
from app.graph.state import WorkflowState, ReviewResult
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


async def reviewer_node(state: WorkflowState) -> dict:
    llm = get_llm(temperature=0.0)
    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))

    draft = state.get("draft", "")
    research = state.get("research_results") or {}

    context = (
        f"Original user request: {state['user_request']}\n\n"
        f"Research confidence: {research.get('confidence', 'unknown')}\n"
        f"Research findings count: {len(research.get('findings', []))}\n\n"
        f"Draft to review:\n{draft}\n\n"
        "Review this draft carefully and respond with JSON."
    )

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM),
        HumanMessage(content=context),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        review: ReviewResult = {
            "status": result.get("status", "fail"),
            "issues": result.get("issues", []),
            "missing_information": result.get("missing_information", []),
            "recommendation": result.get("recommendation", ""),
        }

        review_cycles = state.get("review_cycles", 0) + 1
        max_review_cycles = state.get("max_review_cycles", 3)

        # Force pass if max review cycles reached to prevent infinite loop
        if review_cycles >= max_review_cycles and review["status"] == "fail":
            logger.warning(f"Max review cycles ({max_review_cycles}) reached, forcing pass")
            review["status"] = "pass"
            review["recommendation"] = "Accepted after reaching maximum review cycles"

        logger.info(f"Reviewer: {review['status'].upper()} (cycle {review_cycles}/{max_review_cycles})")

        return {
            "review_result": review,
            "review_cycles": review_cycles,
            "current_agent": "reviewer",
            "messages": [HumanMessage(content=f"[Reviewer] {review['status'].upper()}: {review['recommendation'][:200]}")],
        }

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Reviewer returned non-JSON: {e}")
        review: ReviewResult = {
            "status": "pass",
            "issues": [],
            "missing_information": [],
            "recommendation": "Accepted (reviewer response parsing issue)",
        }
        return {
            "review_result": review,
            "review_cycles": state.get("review_cycles", 0) + 1,
            "current_agent": "reviewer",
            "messages": [HumanMessage(content=f"[Reviewer] PASS (parse fallback)")],
        }

    except Exception as e:
        logger.error(f"Reviewer node failed: {e}")
        retry_counts["reviewer"] = retry_counts.get("reviewer", 0) + 1
        errors.append({
            "agent": "reviewer",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_counts["reviewer"],
        })
        return {
            "review_result": {"status": "pass", "issues": [], "missing_information": [], "recommendation": "Accepted after reviewer failure"},
            "review_cycles": state.get("review_cycles", 0) + 1,
            "current_agent": "reviewer",
            "errors": errors,
            "retry_counts": retry_counts,
            "messages": [HumanMessage(content=f"[Reviewer] Failed, defaulting to PASS: {str(e)}")],
        }
