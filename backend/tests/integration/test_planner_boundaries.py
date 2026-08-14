from app.domain.itinerary import ActivityKind
from app.planning import DeterministicPlanner, PlannerConfig, PlanningStatus
from app.scripts.generate_fixture_plan import build_fixture_facts


def facts_with_constraints(**updates):
    """通过完整模型校验构造约束发生变化的规划事实。"""
    facts = build_fixture_facts()
    request_data = facts.request.model_dump(mode="python")
    request_data["constraints"].update(updates)
    request = type(facts.request).model_validate(request_data)
    return type(facts)(
        request=request,
        places=facts.places,
        weather=facts.weather,
        route_matrix=facts.route_matrix,
        exchange_rates=facts.exchange_rates,
        planned_at=facts.planned_at,
    )


def visit_activities(outcome):
    """按行程顺序返回所有游览活动。"""
    return [
        activity
        for day in outcome.itinerary.days
        for activity in day.activities
        if activity.kind == ActivityKind.VISIT
    ]


def test_low_budget_removes_expensive_places_with_bounded_repairs() -> None:
    """低预算场景应删除高费用地点，并在有限轮次内得到可行结果。"""
    facts = facts_with_constraints(total_budget={"amount": 50_000, "currency": "CNY"})

    outcome = DeterministicPlanner().plan(facts)

    assert outcome.status == PlanningStatus.FEASIBLE
    assert outcome.attempts == 4
    assert outcome.itinerary.budget.planned_total.amount <= 50_000
    assert len(outcome.repair_notes) == 3
    assert {activity.title for activity in visit_activities(outcome)}.isdisjoint(
        {"teamLab Borderless", "SHIBUYA SKY", "三鹰之森吉卜力美术馆"}
    )


def test_zero_repair_limit_returns_unsatisfied_after_first_attempt() -> None:
    """修正上限为零时立即返回最后报告，不能进入隐藏循环。"""
    facts = facts_with_constraints(total_budget={"amount": 50_000, "currency": "CNY"})

    outcome = DeterministicPlanner(PlannerConfig(max_repair_rounds=0)).plan(facts)

    assert outcome.status == PlanningStatus.UNSATISFIED
    assert outcome.attempts == 1
    assert any(item.code == "BUDGET_EXCEEDED" for item in outcome.report.violations)


def test_low_walking_limit_stays_within_daily_maximum() -> None:
    """较低步行上限下，排程器不会继续插入会超限的路线。"""
    facts = facts_with_constraints(max_walking_meters_per_day=1_000)

    outcome = DeterministicPlanner().plan(facts)

    assert outcome.status == PlanningStatus.FEASIBLE
    assert all(day.statistics.walking_meters <= 1_000 for day in outcome.itinerary.days)
    assert not any(item.code == "MAX_WALKING_EXCEEDED" for item in outcome.report.violations)


def test_fixture_plan_contains_indoor_and_outdoor_visits() -> None:
    """普通天气的完整样例应同时覆盖室内和室外游览。"""
    outcome = DeterministicPlanner().plan(build_fixture_facts())
    visit_types = {activity.indoor_outdoor for activity in visit_activities(outcome)}

    assert "indoor" in visit_types
    assert "outdoor" in visit_types


def test_planner_does_not_modify_facts_and_generates_unique_ids() -> None:
    """规划过程只读消费事实，并为全部派生对象生成唯一稳定 ID。"""
    facts = build_fixture_facts()
    request_before = facts.request.model_dump_json()
    places_before = tuple(place.model_dump_json() for place in facts.places)
    routes_before = facts.route_matrix.model_dump_json()

    outcome = DeterministicPlanner().plan(facts)

    assert facts.request.model_dump_json() == request_before
    assert tuple(place.model_dump_json() for place in facts.places) == places_before
    assert facts.route_matrix.model_dump_json() == routes_before

    activity_ids = [activity.id for day in outcome.itinerary.days for activity in day.activities]
    route_ids = [route.id for day in outcome.itinerary.days for route in day.route_legs]
    budget_ids = [item.id for item in outcome.itinerary.budget.items]
    assert len(activity_ids) == len(set(activity_ids))
    assert len(route_ids) == len(set(route_ids))
    assert len(budget_ids) == len(set(budget_ids))
