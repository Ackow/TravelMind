from threading import RLock
from uuid import UUID

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)


class InMemoryTravelRepository:
    """适合单进程教学和测试的线程安全内存仓库。

    所有读写都使用 deep copy，防止调用方绕过 save 方法原地修改仓库内容。
    """

    def __init__(self) -> None:
        self._trips: dict[UUID, TripRecord] = {}
        self._runs: dict[tuple[UUID, UUID], PlanningRunRecord] = {}
        self._plans: dict[tuple[UUID, int], PlanVersionRecord] = {}
        self._events: dict[UUID, list[PlanningEventRecord]] = {}
        self._feedback: dict[UUID, FeedbackRecord] = {}
        self._lock = RLock()

    @staticmethod
    def _copy(value):
        return value.model_copy(deep=True)

    # 新增旅行记录
    def add_trip(self, trip: TripRecord) -> None:
        with self._lock:
            if trip.id in self._trips:
                raise ValueError("trip already exists")
            self._trips[trip.id] = self._copy(trip)

    # 按 ID 获取旅行记录
    def get_trip(self, trip_id: UUID) -> TripRecord | None:
        with self._lock:
            value = self._trips.get(trip_id)
            return None if value is None else self._copy(value)

    # 保存/更新旅行记录
    def save_trip(self, trip: TripRecord) -> None:
        with self._lock:
            if trip.id not in self._trips:
                raise ValueError("trip does not exist")
            self._trips[trip.id] = self._copy(trip)

    # 新增规划任务记录
    def add_run(self, run: PlanningRunRecord) -> None:
        with self._lock:
            key = (run.trip_id, run.id)
            if key in self._runs:
                raise ValueError("planning run already exists")
            self._runs[key] = self._copy(run)

    # 按旅行和任务 ID 获取规划记录
    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord | None:
        with self._lock:
            value = self._runs.get((trip_id, run_id))
            return None if value is None else self._copy(value)

    # 保存/更新规划任务记录
    def save_run(self, run: PlanningRunRecord) -> None:
        with self._lock:
            key = (run.trip_id, run.id)
            if key not in self._runs:
                raise ValueError("planning run does not exist")
            self._runs[key] = self._copy(run)

    # 新增计划版本
    def add_plan(self, plan: PlanVersionRecord) -> None:
        with self._lock:
            key = (plan.trip_id, plan.version)
            if key in self._plans:
                raise ValueError("plan version already exists")
            self._plans[key] = self._copy(plan)

    # 保存/更新计划版本
    def save_plan(self, plan: PlanVersionRecord) -> None:
        with self._lock:
            key = (plan.trip_id, plan.version)
            if key not in self._plans:
                raise ValueError("plan version does not exist")
            self._plans[key] = self._copy(plan)

    # 按旅行 ID 和版本号获取计划
    def get_plan(self, trip_id: UUID, version: int) -> PlanVersionRecord | None:
        with self._lock:
            value = self._plans.get((trip_id, version))
            return None if value is None else self._copy(value)

    # 获取旅行的全部计划版本
    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]:
        with self._lock:
            values = [
                self._copy(plan)
                for (known_trip_id, _), plan in self._plans.items()
                if known_trip_id == trip_id
            ]
        return sorted(values, key=lambda item: item.version)

    # 新增规划事件
    def add_event(self, event: PlanningEventRecord) -> None:
        with self._lock:
            self._events.setdefault(event.run_id, []).append(self._copy(event))

    # 获取某次规划任务的全部事件
    def list_events(self, run_id: UUID) -> list[PlanningEventRecord]:
        with self._lock:
            return [self._copy(item) for item in self._events.get(run_id, [])]

    # 新增用户反馈
    def add_feedback(self, feedback: FeedbackRecord) -> None:
        with self._lock:
            if feedback.id in self._feedback:
                raise ValueError("feedback already exists")
            self._feedback[feedback.id] = self._copy(feedback)

    # 保存/更新用户反馈
    def save_feedback(self, feedback: FeedbackRecord) -> None:
        with self._lock:
            if feedback.id not in self._feedback:
                raise ValueError("feedback does not exist")
            self._feedback[feedback.id] = self._copy(feedback)
