from fastapi import APIRouter, Depends, Request

from app.api.middleware.rate_limit import check_rate_limit
from app.tools.registry import get_all_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools(request: Request, _: None = Depends(check_rate_limit)):
    """Return all registered MCP tool schemas."""
    return {"tools": get_all_tools()}
