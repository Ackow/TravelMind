from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import ClockDep, RepositoryDep
from app.api.schemas import TripCreateRequest, TripResponse
from app.application.errors import ApplicationError
from app.application.models import TripRecord
from app.application.trips import create_trip, get_trip

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


def to_trip_response(trip: TripRecord) -> TripResponse:
    # 从trip对象中提取原始请求数据
    request = trip.request

    return TripResponse(
        id=trip.id,
        status=trip.status,
        revision=trip.revision,
        origin=request.origin,
        destination=request.destination,
        destination_timezone=request.destination_timezone,
        date_range=request.date_range,
        travelers=request.travelers,
        preferences=request.preferences,
        constraints=request.constraints,
        locale=request.locale,
        display_currency=request.display_currency,
        notes=request.notes,
        current_plan_version=trip.current_plan_version,
        active_planning_run_id=trip.active_planning_run_id,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="created_trip",
)
def create_trip_endpoint(
    payload: TripCreateRequest,
    response: Response,
    repository: RepositoryDep,
    clock: ClockDep,
) -> TripResponse:
    """创建新旅行的API端点"""

    trip = create_trip(payload, repository=repository, clock=clock)
    # 设置 Location 响应头，指向新创建资源的URL
    response.headers["Location"] = f"/api/v1/trips/{trip.id}"
    # 设置 ETag 响应头，值为当前资源版本号，用于客户端缓存和并发控制
    response.headers["ETag"] = f'"{trip.revision}"'

    return to_trip_response(trip)


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="get_trip",
)
def get_trip_response(
    trip_id: UUID,
    repository: RepositoryDep,
) -> TripResponse:
    trip = get_trip(repository, trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    return to_trip_response(trip)
