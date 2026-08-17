from typing import Protocol
from uuid import UUID

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)


class TravelRepository(Protocol):
    """应用层需要的存储能力，不暴露字典或数据库细节。"""

    def add_trip(self, trip: TripRecord) -> None:
        """新增一个旅行记录。"""

    def get_trip(self, trip_id: UUID) -> TripRecord | None:
        """按 ID 获取旅行记录，不存在时返回 None。"""

    def save_trip(self, trip: TripRecord) -> None:
        """保存/更新一个已存在的旅行记录。"""

    def add_run(self, run: PlanningRunRecord) -> None:
        """新增一次规划任务记录。"""

    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord | None:
        """按旅行 ID 和规划任务 ID 获取规划记录。"""

    def save_run(self, run: PlanningRunRecord) -> None:
        """保存/更新一次规划任务记录。"""

    def add_plan(self, plan: PlanVersionRecord) -> None:
        """新增一个计划版本。"""

    def save_plan(self, plan: PlanVersionRecord) -> None:
        """保存/更新一个计划版本。"""

    def get_plan(self, trip_id: UUID, version: int) -> PlanVersionRecord | None:
        """按旅行 ID 和版本号获取计划版本。"""

    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]:
        """获取某个旅行的全部计划版本。"""

    def add_event(self, event: PlanningEventRecord) -> None:
        """新增一条规划过程事件。"""

    def list_events(self, run_id: UUID) -> list[PlanningEventRecord]:
        """获取某次规划任务的全部事件。"""

    def add_feedback(self, feedback: FeedbackRecord) -> None:
        """新增一条用户反馈。"""

    def save_feedback(self, feedback: FeedbackRecord) -> None:
        """保存/更新一条用户反馈。"""
