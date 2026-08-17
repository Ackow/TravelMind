from datetime import datetime
from typing import Protocol

from app.domain.trip import TripRequest
from app.planning import PlanningFacts


class FactsFactory(Protocol):
    """把外部事实转换成规划器只读输入。"""

    def build(self, request: TripRequest, planned_at: datetime) -> PlanningFacts: ...
