from uuid import UUID, uuid4

from app.application.clock import Clock
from app.application.models import TripRecord, TripStatus
from app.application.repository import TravelRepository
from app.domain.trip import TripRequest


def create_trip(
    request: TripRequest,
    *,
    repository: TravelRepository,
    clock: Clock,
) -> TripRecord:
    """创建旅行并通过 Repository 保存。"""

    now = clock.now()
    trip = TripRecord(
        id=uuid4(),
        status=TripStatus.DRAFT,
        revision=1,
        request=request,
        created_at=now,
        updated_at=now,
    )
    repository.add_trip(trip)
    return trip


def get_trip(repository: TravelRepository, trip_id: UUID) -> TripRecord | None:
    """按 ID 获取旅行记录。"""
    return repository.get_trip(trip_id)


def save_trip(repository: TravelRepository, trip: TripRecord) -> None:
    """保存旅行记录。"""
    repository.save_trip(trip)
