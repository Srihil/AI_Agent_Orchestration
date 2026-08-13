import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.memory import Memory

logger = logging.getLogger(__name__)

MEMORY_TYPES = {"preference", "outcome", "fact"}


async def get_relevant_memories(session: AsyncSession, user_id: str, query: str = None) -> str:
    """Retrieve user memories, optionally filtered by query keywords."""
    stmt = select(Memory).where(Memory.user_id == user_id).order_by(Memory.updated_at.desc()).limit(20)
    result = await session.execute(stmt)
    memories = result.scalars().all()

    if not memories:
        return ""

    if query:
        query_lower = query.lower()
        memories = [m for m in memories if query_lower in m.content.lower()] or memories[:5]

    lines = []
    for m in memories[:10]:
        lines.append(f"[{m.memory_type}] {m.content}")

    return "\n".join(lines)


async def save_memory(session: AsyncSession, user_id: str, content: str, memory_type: str = "fact") -> Memory:
    if memory_type not in MEMORY_TYPES:
        memory_type = "fact"
    memory = Memory(user_id=user_id, content=content, memory_type=memory_type)
    session.add(memory)
    await session.commit()
    await session.refresh(memory)
    return memory


async def list_memories(session: AsyncSession, user_id: str, memory_type: str = None) -> list[Memory]:
    stmt = select(Memory).where(Memory.user_id == user_id).order_by(Memory.created_at.desc())
    if memory_type and memory_type != "all":
        stmt = stmt.where(Memory.memory_type == memory_type)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_memory(session: AsyncSession, memory_id: str, user_id: str, content: str, memory_type: str) -> Memory | None:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return None
    memory.content = content
    if memory_type in MEMORY_TYPES:
        memory.memory_type = memory_type
    await session.commit()
    await session.refresh(memory)
    return memory


async def delete_memory(session: AsyncSession, memory_id: str, user_id: str) -> bool:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return False
    await session.delete(memory)
    await session.commit()
    return True
