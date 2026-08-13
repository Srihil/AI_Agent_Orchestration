import json
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.config.prompts import ANALYST_SYSTEM
from app.graph.state import WorkflowState, AnalysisResult
from app.services.llm_service import get_llm
from app.tools.registry import get_tools_for_agent

logger = logging.getLogger(__name__)


async def analyst_node(state: WorkflowState) -> dict:
    tools = get_tools_for_agent("analyst")
    llm = get_llm(temperature=0.1).bind_tools(tools) if tools else get_llm(temperature=0.1)

    research = state.get("research_results") or {}
    tool_results = list(state.get("tool_results", []))
    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))

    context = (
        f"User's original request: {state['user_request']}\n\n"
        f"Research summary: {research.get('summary', 'No research available')}\n\n"
        f"Research findings:\n" + "\n".join(f"- {f}" for f in research.get("findings", [])) + "\n\n"
        f"Sources: {', '.join(research.get('sources', [])) or 'None'}\n\n"
        "Analyze this information and provide structured analysis as JSON."
    )

    messages = [
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=context),
    ]

    try:
        tool_map = {t.name: t for t in tools}

        for iteration in range(8):
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
                                "input": json.dumps(tc["args"])[:200],
                                "output": str(result)[:500],
                                "success": True,
                                "agent": "analyst",
                            })
                        except Exception as e:
                            tm = ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"])
                            tool_results.append({
                                "tool_name": tc["name"],
                                "input": json.dumps(tc["args"])[:200],
                                "output": f"Error: {str(e)}",
                                "success": False,
                                "agent": "analyst",
                            })
                        messages.append(tm)
            else:
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                try:
                    result = json.loads(content)
                    analysis: AnalysisResult = {
                        "summary": result.get("summary", ""),
                        "key_points": result.get("key_points", []),
                        "patterns": result.get("patterns", []),
                        "conclusion": result.get("conclusion", ""),
                    }
                    logger.info(f"Analyst completed: {analysis['summary'][:100]}")
                    return {
                        "analysis_results": analysis,
                        "current_agent": "analyst",
                        "tool_results": tool_results,
                        "messages": [HumanMessage(content=f"[Analyst] Completed: {analysis['summary'][:200]}")],
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Analyst returned non-JSON, wrapping: {e}")
                    analysis: AnalysisResult = {
                        "summary": response.content[:500],
                        "key_points": [response.content[:300]],
                        "patterns": [],
                        "conclusion": response.content[:300],
                    }
                    return {
                        "analysis_results": analysis,
                        "current_agent": "analyst",
                        "tool_results": tool_results,
                        "messages": [HumanMessage(content=f"[Analyst] Completed: {analysis['summary'][:200]}")],
                    }

        raise RuntimeError("Analyst exceeded maximum iterations")

    except Exception as e:
        logger.error(f"Analyst node failed: {e}")
        retry_counts["analyst"] = retry_counts.get("analyst", 0) + 1
        errors.append({
            "agent": "analyst",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_counts["analyst"],
        })
        return {
            "current_agent": "analyst",
            "errors": errors,
            "retry_counts": retry_counts,
            "tool_results": tool_results,
            "messages": [HumanMessage(content=f"[Analyst] Failed: {str(e)}")],
        }
