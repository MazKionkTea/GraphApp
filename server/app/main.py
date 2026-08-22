"""Graph App — FastAPI main entry."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routes import health, mindmaps, workflows, projects

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("graph-app")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Unified Mind Map, Workflow, and Code Graph visualizer backend",
)

# CORS — allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(mindmaps.router)
app.include_router(workflows.router)
app.include_router(workflows.actions_router)
app.include_router(projects.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"Graph App backend started (v{settings.version})")
    logger.info(f"DB: {settings.db_path}")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health",
    }
