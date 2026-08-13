from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryOut
from app.services.auth_service import get_current_user
from app.memory.manager import save_memory, list_memories, update_memory, delete_memory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=list[MemoryOut])
async def get_memories(
    memory_type: str = "all",
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memories = await list_memories(session, current_user.id, memory_type)
    return memories


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(
    body: MemoryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await save_memory(session, current_user.id, body.content, body.memory_type)


@router.put("/{memory_id}", response_model=MemoryOut)
async def update_memory_endpoint(
    memory_id: str,
    body: MemoryUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = await update_memory(
        session, memory_id, current_user.id,
        content=body.content or "",
        memory_type=body.memory_type or "fact",
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=204)
async def delete_memory_endpoint(
    memory_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await delete_memory(session, memory_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
