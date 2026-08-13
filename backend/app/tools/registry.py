from app.tools.calculator import calculator
from app.tools.search import web_search
from app.tools.datetime_tool import get_current_datetime
from app.tools.memory_search import memory_search

# Full tool catalog
ALL_TOOLS = [calculator, web_search, get_current_datetime, memory_search]

# Per-agent tool authorization
AGENT_TOOLS: dict[str, list] = {
    "researcher": [web_search, get_current_datetime, calculator, memory_search],
    "analyst": [calculator, memory_search],
    "writer": [memory_search],
    "reviewer": [],
    "supervisor": [],
}


def get_tools_for_agent(agent_name: str) -> list:
    return AGENT_TOOLS.get(agent_name, [])


def get_tool_by_name(name: str):
    tool_map = {t.name: t for t in ALL_TOOLS}
    return tool_map.get(name)
