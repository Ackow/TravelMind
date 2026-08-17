from datetime import timedelta
from math import ceil
from uuid import UUID, uuid5

from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.domain.common import Money
from app.domain.itinerary import (
    BudgetCategory,
    BudgetItem,
    BudgetSummary,
    DayPlan,
    Itinerary,
)
from app.domain.research import OutdoorSuitability
from app.planning.models import (
    PlannerConfig,
    PlanningFacts,
    PlanningOutcome,
    PlanningStatus,
    Zone,
)
from app.planning.money import MoneyConverter
from app.planning.repair import choose_repair
from app.planning.scheduler import DayScheduler
from app.planning.scoring import rank_places_for_day
from app.planning.zoning import build_zones


def build_budget_summary(
    *,
    request_budget: Money,
    items: list[BudgetItem],
    exchange_rates,
) -> BudgetSummary:
    """根据明细重新计算总额、分类汇总和剩余金额。"""
    category_amounts: dict[BudgetCategory, int] = {}
    for item in items:
        category_amounts[item.category] = (
            category_amounts.get(item.category, 0) + item.amount.amount
        )
    planned_amount = sum(item.amount.amount for item in items)
    remaining = request_budget.amount - planned_amount
    return BudgetSummary(
        limit=request_budget,
        items=items,
        totals_by_category={
            category: Money(
                amount=amount,
                currency=request_budget.currency,
            )
            for category, amount in category_amounts.items()
        },
        planned_total=Money(
            amount=planned_amount,
            currency=request_budget.currency,
        ),
        remaining_amount=remaining,
        currency=request_budget.currency,
        within_budget=remaining >= 0,
        exchange_rates=dict(exchange_rates),
    )


def assign_zones_to_days(
    *,
    dates,
    zones: tuple[Zone, ...],
    scores_by_date: dict,
    weather_by_date: dict,
) -> dict:
    """先为恶劣天气日期选择室内评分最高的区域，再处理普通日期。"""
    weather_priority = {
        OutdoorSuitability.POOR: 0,
        OutdoorSuitability.UNKNOWN: 1,
        OutdoorSuitability.ACCEPTABLE: 2,
        OutdoorSuitability.GOOD: 3,
    }
    ordered_dates = sorted(
        dates,
        key=lambda current: (
            weather_priority.get(
                weather_by_date[current].outdoor_suitability,
                1,
            )
            if current in weather_by_date
            else 1,
            current,
        ),
    )
    remaining = list(zones)
    assignments = {}
    for current_date in ordered_dates:
        if not remaining:
            assignments[current_date] = None
            continue
        daily_scores = {item.place_id: item.score for item in scores_by_date[current_date]}
        selected = min(
            remaining,
            key=lambda zone: (
                -sum(daily_scores.get(place_id, -1000) for place_id in zone.place_ids),
                zone.id,
            ),
        )
        assignments[current_date] = selected
        remaining.remove(selected)
    return assignments


class DeterministicPlanner:
    """确定性行程规划器。"""

    def __init__(self, config: PlannerConfig | None = None) -> None:
        """初始化规划器配置。"""
        self._config = config or PlannerConfig()

    def _build_once(
        self,
        facts: PlanningFacts,
        blocked_place_ids: frozenset[str],
    ) -> Itinerary:
        """基于当前事实和屏蔽地点构建一次完整行程。"""
        request = facts.request
        converter = MoneyConverter(facts.exchange_rates)
        weather_by_date = {item.date: item for item in facts.weather}
        dates = [
            request.date_range.start_date + timedelta(days=offset)
            for offset in range(request.date_range.day_count)
        ]
        scores_by_date = {
            current_date: rank_places_for_day(
                target_date=current_date,
                places=facts.places,
                weather_by_date=weather_by_date,
                request=request,
                converter=converter,
                blocked_place_ids=blocked_place_ids,
            )
            for current_date in dates
        }

        eligible_ids = {item.place_id for scores in scores_by_date.values() for item in scores}
        eligible_places = tuple(place for place in facts.places if place.id in eligible_ids)
        zone_count = min(
            len(dates),
            ceil(len(eligible_places) / self._config.target_zone_size) if eligible_places else 0,
        )
        zones = (
            build_zones(
                places=eligible_places,
                route_matrix=facts.route_matrix,
                target_zone_count=zone_count,
            )
            if zone_count > 0
            else ()
        )
        assignments = assign_zones_to_days(
            dates=dates,
            zones=zones,
            scores_by_date=scores_by_date,
            weather_by_date=weather_by_date,
        )

        scheduler = DayScheduler(
            request=request,
            places=facts.places,
            route_matrix=facts.route_matrix,
            converter=converter,
            config=self._config,
        )
        days: list[DayPlan] = []
        budget_items: list[BudgetItem] = []
        for day_number, current_date in enumerate(dates, start=1):
            zone = assignments[current_date]
            zone_ids = set(zone.place_ids) if zone is not None else set()
            candidates = [
                item for item in scores_by_date[current_date] if item.place_id in zone_ids
            ]
            schedule = scheduler.schedule(
                target_date=current_date,
                day_number=day_number,
                weather=weather_by_date.get(current_date),
                candidates=candidates,
            )
            days.append(schedule.day)
            budget_items.extend(schedule.budget_items)

        return Itinerary(
            trip_id=stable_trip_id(facts),
            title=f"{request.destination} {request.date_range.day_count} 日游",
            destination=request.destination,
            timezone=request.destination_timezone,
            date_range=request.date_range,
            days=days,
            budget=build_budget_summary(
                request_budget=request.constraints.total_budget,
                items=budget_items,
                exchange_rates=facts.exchange_rates,
            ),
            general_notes=["由阶段 3 确定性规划器生成"],
            generated_at=facts.planned_at,
        )

    def plan(self, facts: PlanningFacts) -> PlanningOutcome:
        """规划、检查并执行有限修正。"""
        engine = create_default_engine()
        places_by_id = {place.id: place for place in facts.places}
        context = ConstraintContext(
            request=facts.request,
            places_by_id=places_by_id,
            checked_at=facts.planned_at,
        )
        blocked: frozenset[str] = frozenset()
        repair_notes: list[str] = []

        for round_index in range(self._config.max_repair_rounds + 1):
            itinerary = self._build_once(facts, blocked)
            report = engine.check(itinerary, context)
            if report.passed:
                return PlanningOutcome(
                    status=PlanningStatus.FEASIBLE,
                    itinerary=itinerary,
                    report=report,
                    attempts=round_index + 1,
                    repair_notes=tuple(repair_notes),
                )

            decision = choose_repair(
                report=report,
                itinerary=itinerary,
                request=facts.request,
                places_by_id=places_by_id,
            )
            if decision is None or round_index == self._config.max_repair_rounds:
                return PlanningOutcome(
                    status=PlanningStatus.UNSATISFIED,
                    itinerary=itinerary,
                    report=report,
                    attempts=round_index + 1,
                    repair_notes=tuple(repair_notes),
                )

            blocked = blocked | {decision.blocked_place_id}
            repair_notes.append(decision.reason)

        raise AssertionError("finite planning loop must always return")


def stable_trip_id(facts: PlanningFacts) -> UUID:
    """根据请求内容生成稳定的旅行 ID。"""
    namespace = UUID("8e5c513c-4d70-4df8-8ab4-38c61c4b3002")
    return uuid5(namespace, facts.request.model_dump_json())
