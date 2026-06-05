from app.api.routes.auth import router as auth_router
from app.api.routes.coding import router as coding_router
from app.api.routes.admin import router as admin_router

__all__ = ["auth_router", "coding_router", "admin_router"]
