import json
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from app.config.prompts import RESEARCHER_SYSTEM
from app.graph.state import WorkflowState, ResearchResult
from app.services.llm_service import get_llm
from app.tools.registry import get_tools_for_agent

logger = logging.getLogger(__name__)


async def _run_tool_calls(tool_calls: list, tools: list[BaseTool]) -> list[ToolMessage]:
    tool_map = {t.name: t for t in tools}
    messages = []
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        tool = tool_map.get(tool_name)
        if not tool:
            messages.append(ToolMessage(content=f"Tool {tool_name} not available", tool_call_id=tc["id"]))
            continue
        try:
            result = await tool.ainvoke(tool_args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        except Exception as e:
            messages.append(ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"]))
    return messages


async def researcher_node(state: WorkflowState) -> dict:
    tools = get_tools_for_agent("researcher")
    llm = get_llm(temperature=0.1).bind_tools(tools)

    supervisor_instructions = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "content") and "[Supervisor]" in msg.content and "researcher" in msg.content.lower():
            supervisor_instructions = msg.content
            break

    user_prompt = (
        f"Task: {state['user_request']}\n\n"
        f"Instructions: {supervisor_instructions}\n\n"
        "Research this thoroughly using the available tools. "
        "Gather information from multiple search queries if needed. "
        "Then provide your structured research results as JSON."
    )

    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))
    tool_results = list(state.get("tool_results", []))

    try:
        # Agentic loop: LLM calls tools until it produces a final response
        for iteration in range(10):
            response = await llm.ainvoke(messages)
            messages.append(response)

            if response.tool_calls:
                tool_messages = await _run_tool_calls(response.tool_calls, tools)
                messages.extend(tool_messages)
                for tc, tm in zip(response.tool_calls, tool_messages):
                    tool_results.append({
                        "tool_name": tc["name"],
                        "input": json.dumps(tc["args"])[:200],
                        "output": tm.content[:500],
                        "success": not tm.content.startswith("Tool error"),
                        "agent": "researcher",
                    })
            else:
                # Final response — parse JSON
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                try:
                    result = json.loads(content)
                    research: ResearchResult = {
                        "summary": result.get("summary", ""),
                        "findings": result.get("findings", []),
                        "sources": result.get("sources", []),
                        "confidence": float(result.get("confidence", 0.7)),
                    }
                    logger.info(f"Researcher completed with confidence {research['confidence']}")
                    return {
                        "research_results": research,
                        "current_agent": "researcher",
                        "tool_results": tool_results,
                        "messages": [HumanMessage(content=f"[Researcher] Completed: {research['summary'][:200]}")],
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    # If LLM didn't return proper JSON, wrap the response
                    logger.warning(f"Researcher returned non-JSON, wrapping: {e}")
                    research: ResearchResult = {
                        "summary": response.content[:500],
                        "findings": [response.content[:500]],
                        "sources": [],
                        "confidence": 0.5,
                    }
                    return {
                        "research_results": research,
                        "current_agent": "researcher",
                        "tool_results": tool_results,
                        "messages": [HumanMessage(content=f"[Researcher] Completed (unstructured): {research['summary'][:200]}")],
                    }

        # Max iterations reached without a final response
        raise RuntimeError("Researcher exceeded maximum tool call iterations")

    except Exception as e:
        logger.error(f"Researcher node failed: {e}")
        retry_counts["researcher"] = retry_counts.get("researcher", 0) + 1
        errors.append({
            "agent": "researcher",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_counts["researcher"],
        })

        if retry_counts["researcher"] < state.get("max_retries", 3):
            return {
                "current_agent": "researcher",
                "errors": errors,
                "retry_counts": retry_counts,
                "tool_results": tool_results,
                "messages": [HumanMessage(content=f"[Researcher] Failed (retry {retry_counts['researcher']}): {str(e)}")],
            }

        # Max retries exceeded — provide empty research so workflow can continue
        return {
            "research_results": {
                "summary": "Research could not be completed due to repeated failures.",
                "findings": [],
                "sources": [],
                "confidence": 0.0,
            },
            "current_agent": "researcher",
            "errors": errors,
            "retry_counts": retry_counts,
            "tool_results": tool_results,
            "messages": [HumanMessage(content=f"[Researcher] Failed after {retry_counts['researcher']} retries: {str(e)}")],
        }
