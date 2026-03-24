from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.auth import AuthMiddleware
from app.api.routes import agent, eval, tenants, tools
from app.db.session import init_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AgentGateway")
    await init_db()
    yield
    logger.info("Shutting down AgentGateway")


app = FastAPI(
    title="AgentGateway",
    description="MCP-compatible integration gateway for LLM agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(agent.router)
app.include_router(eval.router)
app.include_router(tools.router)
app.include_router(tenants.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AgentGateway"}
