"""FastAPI application: lifecycle, routes, scheduler."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db import create_tables, init_db
from app.utils.logging import setup_logging, get_logger
from app.routes import (
    generate_router,
    publish_router,
    analytics_router,
    accounts_router,
    history_router,
)
from app.routes.generate import regenerate_router
from app.routes.storage import router as storage_router
from app.routes.publish import set_scheduler

logger = get_logger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: logging, DB tables, scheduler. Shutdown: scheduler."""
    setup_logging()
    init_db()
    try:
        await create_tables()
    except Exception as e:
        logger.warning("create_tables_failed", error=str(e))
    scheduler = BackgroundScheduler()
    scheduler.start()
    set_scheduler(scheduler)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="LinkedIn AI Agent",
    description="AI-powered LinkedIn post generation and smart publishing",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(generate_router)
app.include_router(regenerate_router)  # POST /regenerate
app.include_router(publish_router)
app.include_router(analytics_router)
app.include_router(accounts_router)
app.include_router(history_router)
app.include_router(storage_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/auth/linkedin/callback")
async def linkedin_callback_redirect(request: Request):
    """Redirect to accounts callback so LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback works."""
    return RedirectResponse(url=f"/accounts/auth/linkedin/callback?{request.url.query}", status_code=302)


@app.get("/")
async def dashboard():
    """Serve the dashboard UI."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Dashboard not found. Run from project root so static/ is available."}


@app.get("/health")
async def health():
    return {"status": "ok"}
