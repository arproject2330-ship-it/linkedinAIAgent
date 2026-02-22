"""API route modules."""
from app.routes.generate import router as generate_router
from app.routes.publish import router as publish_router
from app.routes.analytics import router as analytics_router
from app.routes.accounts import router as accounts_router
from app.routes.history import router as history_router

__all__ = [
    "generate_router",
    "publish_router",
    "analytics_router",
    "accounts_router",
    "history_router",
]
