import secrets
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Tenant
from app.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/tenants", tags=["tenants"])


class CreateTenantRequest(BaseModel):
    name: str
    rate_limit_rpm: int = 60
    rate_limit_tokens_per_day: int = 1_000_000


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str
    rate_limit_rpm: int
    rate_limit_tokens_per_day: int


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(body: CreateTenantRequest, db: AsyncSession = Depends(get_db)):
    api_key = f"{settings.api_key_prefix}{secrets.token_urlsafe(32)}"
    tenant = Tenant(
        name=body.name,
        api_key=api_key,
        rate_limit_rpm=body.rate_limit_rpm,
        rate_limit_tokens_per_day=body.rate_limit_tokens_per_day,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    logger.info("tenant_created", name=tenant.name, id=str(tenant.id))
    return tenant
