import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.models import Tenant
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger()

# Routes that don't require auth
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/tenants"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing X-API-Key header"},
            )

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.api_key == api_key, Tenant.is_active == True)
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid or inactive API key"},
            )

        request.state.tenant = tenant
        logger.info("request_authenticated", tenant=tenant.name, path=request.url.path)
        return await call_next(request)
