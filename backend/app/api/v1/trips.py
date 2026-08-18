from uuid import UUID
from fastapi import APIRouter, Response, status
from app.api.dependencies import ClockDep, RepositoryDep
from app.api.schemas import TripCreateRequest, TripResponse
from app.application.errors import ApplicationError
from app.application.models import TripRecord
from app.application.trips import create_trip, get_trip

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


def to_trip_response(trip: TripRecord) -> TripResponse:
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
    operation_id="create_trip",
)
def create_trip_endpoint(
    payload: TripCreateRequest,
    response: Response,
    repository: RepositoryDep,
    clock: ClockDep,
) -> TripResponse:
    trip = create_trip(
        request=payload,
        repository=repository,
        clock=clock,
    )
    response.headers["Location"] = f"/api/v1/trips/{trip.id}"
    response.headers["ETag"] = f'"{trip.revision}"'
    return to_trip_response(trip)


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="get_trip",
)
def get_trip_endpoint(
    trip_id: UUID,
    response: Response,
    repository: RepositoryDep,
) -> TripResponse:
    trip = get_trip(repository, trip_id)
    if trip is None:
        raise ApplicationError(
            code="TRIP_NOT_FOUND",
            message=f"Trip {trip_id} does not exist",
            status_code=404,
        )
    response.headers["ETag"] = f'"{trip.revision}"'
    return to_trip_response(trip)
