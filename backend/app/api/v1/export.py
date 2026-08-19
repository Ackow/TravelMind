from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.dependencies import RepositoryDep
from app.application.errors import ApplicationError
from app.application.export_service import ExportService

router = APIRouter(prefix="/api/v1/trips/{trip_id}/export", tags=["export"])


@router.get("/markdown", response_class=Response)
def export_trip_markdown(
    trip_id: UUID,
    repository: RepositoryDep,
    version: int | None = Query(default=None, description="导出的计划版本号，缺省为当前生效版本"),
) -> Response:
    """将旅行方案导出为标准排版的 Markdown 文本。"""
    export_service = ExportService(repository)
    try:
        content = export_service.export_to_markdown(trip_id=trip_id, version=version)
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="trip_{trip_id}_plan.md"'},
        )
    except ApplicationError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
        )
