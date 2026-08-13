import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api import auth, workflows, approvals, memory, agents, health, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Agent Orchestration System...")
    from app.services.workflow_service import init_graph
    try:
        await init_graph()
        logger.info("LangGraph initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangGraph: {e}")
        # Don't crash on startup — health endpoint will report not_ready
    yield
    from app.services.workflow_service import shutdown_graph
    await shutdown_graph()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Agent Orchestration System",
    description="Stateful multi-agent workflow platform powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "name": "Agent Orchestration System",
        "version": "1.0.0",
        "docs": "/docs",
    }
