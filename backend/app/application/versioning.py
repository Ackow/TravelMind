from uuid import UUID

from app.application.errors import ApplicationError
from app.application.models import PlanVersionRecord, TripRecord
from app.application.repository import TravelRepository


def get_plan_history(repository: TravelRepository, trip_id: UUID) -> list[PlanVersionRecord]:
    """获取指定旅行的完整版本历史（按版本号自增排列）"""
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)
    return repository.list_plans(trip_id)


def checkout_plan_version(
    repository: TravelRepository,
    trip_id: UUID,
    target_version: int,
) -> TripRecord:
    """将旅行当前生效的计划指针回滚/切换至历史指定版本。"""
    trip = repository.get_trip(trip_id)
    if trip is None:
        raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)

    target_plan = repository.get_plan(trip_id, target_version)
    if target_plan is None:
        raise ApplicationError("PLAN_NOT_FOUND", f"目标计划版本 v{target_version} 不存在", 404)

    updated_trip = trip.model_copy(
        update={
            "current_plan_version": target_version,
            "revision": trip.revision + 1,
        }
    )
    repository.save_trip(updated_trip)
    return updated_trip
