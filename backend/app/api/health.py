from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False

    import app.services.workflow_service as _ws
    graph_ok = _ws._compiled_graph is not None

    return {
        "status": "ready" if (db_ok and graph_ok) else "not_ready",
        "database": "ok" if db_ok else "error",
        "graph": "ok" if graph_ok else "not_initialized",
    }
