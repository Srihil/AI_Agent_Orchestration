import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.config.prompts import WRITER_SYSTEM
from app.graph.state import WorkflowState
from app.services.llm_service import get_llm
from app.tools.registry import get_tools_for_agent

logger = logging.getLogger(__name__)


async def writer_node(state: WorkflowState) -> dict:
    tools = get_tools_for_agent("writer")
    llm = get_llm(temperature=0.3).bind_tools(tools) if tools else get_llm(temperature=0.3)

    research = state.get("research_results") or {}
    analysis = state.get("analysis_results") or {}
    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))
    tool_results = list(state.get("tool_results", []))

    # Check for user preferences via memory_search before writing
    memory_note = ""
    if state.get("memory_context"):
        memory_note = f"\n\nUser preferences from memory:\n{state['memory_context']}"

    context = (
        f"User's original request: {state['user_request']}\n\n"
        f"Research summary: {research.get('summary', '')}\n"
        f"Research findings:\n" + "\n".join(f"- {f}" for f in research.get("findings", [])) + "\n\n"
        f"Analysis summary: {analysis.get('summary', '')}\n"
        f"Key points:\n" + "\n".join(f"- {p}" for p in analysis.get("key_points", [])) + "\n"
        f"Conclusion: {analysis.get('conclusion', '')}"
        + memory_note + "\n\n"
        "Write a comprehensive, well-structured response to the user's request based on the above information. "
        "Do not add facts not in the source material."
    )

    messages = [
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=context),
    ]

    try:
        tool_map = {t.name: t for t in tools}

        for iteration in range(5):
            response = await llm.ainvoke(messages)
            messages.append(response)

            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool = tool_map.get(tc["name"])
                    if tool:
                        try:
                            result = await tool.ainvoke(tc["args"])
                            tm = ToolMessage(content=str(result), tool_call_id=tc["id"])
                            tool_results.append({
                                "tool_name": tc["name"],
                                "input": str(tc["args"])[:200],
                                "output": str(result)[:500],
                                "success": True,
                                "agent": "writer",
                            })
                        except Exception as e:
                            tm = ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"])
                        messages.append(tm)
            else:
                draft = response.content.strip()
                logger.info(f"Writer produced draft ({len(draft)} chars)")
                return {
                    "draft": draft,
                    "current_agent": "writer",
                    "tool_results": tool_results,
                    "messages": [HumanMessage(content=f"[Writer] Draft produced ({len(draft)} chars)")],
                }

        raise RuntimeError("Writer exceeded maximum iterations")

    except Exception as e:
        logger.error(f"Writer node failed: {e}")
        retry_counts["writer"] = retry_counts.get("writer", 0) + 1
        errors.append({
            "agent": "writer",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_counts["writer"],
        })
        fallback_draft = (
            f"Based on available research: {research.get('summary', 'No research available')}"
            if research.get("summary") else
            f"Unable to generate response: {str(e)}"
        )
        return {
            "draft": fallback_draft,
            "current_agent": "writer",
            "errors": errors,
            "retry_counts": retry_counts,
            "tool_results": tool_results,
            "messages": [HumanMessage(content=f"[Writer] Failed, using fallback: {str(e)}")],
        }
