from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health/live", operation_id="get_liveness", summary="检查 API 进程是否存活")
def get_liveness() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": "travelmind-api", "version": settings.app_version}


@router.get(
    "/health/ready",
    operation_id="get_readiness",
    summary="检查 API 是否可以接收请求",
)
def get_readiness() -> dict[str, object]:
    return {
        "status": "ready",
        "checks": {
            "configuration": "ok",
        },
    }
