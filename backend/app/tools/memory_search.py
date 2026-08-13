import json
import logging
from functools import lru_cache
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Thread-local user context for memory search tool
# Set before invoking agent nodes
_current_user_id: str | None = None


def set_memory_context(user_id: str) -> None:
    global _current_user_id
    _current_user_id = user_id


@tool
def memory_search(query: str, memory_type: str = "all") -> str:
    """Search user's long-term memory for relevant information.

    Args:
        query: Keywords or phrase to search for in memories.
        memory_type: Filter by type — "preference", "outcome", "fact", or "all" (default).

    Returns:
        JSON string with matching memories.
    """
    user_id = _current_user_id
    if not user_id:
        return json.dumps({"memories": [], "note": "No user context available"})

    try:
        import asyncio
        from sqlalchemy import select, or_
        from app.database.session import AsyncSessionLocal
        from app.models.memory import Memory

        async def _fetch():
            async with AsyncSessionLocal() as session:
                stmt = select(Memory).where(Memory.user_id == user_id)
                if memory_type != "all":
                    stmt = stmt.where(Memory.memory_type == memory_type)
                result = await session.execute(stmt)
                memories = result.scalars().all()
                query_lower = query.lower()
                matching = [
                    {
                        "id": m.id,
                        "content": m.content,
                        "type": m.memory_type,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in memories
                    if query_lower in m.content.lower()
                ]
                return matching

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _fetch())
                    matching = future.result(timeout=10)
            else:
                matching = loop.run_until_complete(_fetch())
        except RuntimeError:
            matching = asyncio.run(_fetch())

        return json.dumps({"memories": matching, "total": len(matching)})

    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return json.dumps({"memories": [], "error": str(e)})
