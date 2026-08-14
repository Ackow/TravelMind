from app.domain.itinerary import ActivityKind, Itinerary
from app.planning import DeterministicPlanner, PlanningStatus
from app.scripts.generate_fixture_plan import build_fixture_facts


def test_fixture_planner_generates_feasible_itinerary() -> None:
    facts = build_fixture_facts()

    outcome = DeterministicPlanner().plan(facts)

    assert outcome.status == PlanningStatus.FEASIBLE
    assert outcome.report.passed is True
    assert not any(item.severity == "error" for item in outcome.report.violations)
    assert len(outcome.itinerary.days) == facts.request.date_range.day_count
    assert Itinerary.model_validate_json(outcome.itinerary.model_dump_json()) == outcome.itinerary


def test_poor_weather_day_contains_no_outdoor_visit() -> None:
    facts = build_fixture_facts()
    outcome = DeterministicPlanner().plan(facts)
    weather_by_date = {item.date: item for item in facts.weather}

    for day in outcome.itinerary.days:
        if weather_by_date[day.date].outdoor_suitability != "poor":
            continue
        assert all(
            activity.indoor_outdoor != "outdoor"
            for activity in day.activities
            if activity.kind == ActivityKind.VISIT
        )


def test_daily_statistics_are_derived_from_route_and_budget_facts() -> None:
    outcome = DeterministicPlanner().plan(build_fixture_facts())

    for day in outcome.itinerary.days:
        expected_walking = sum(item.walking_meters for item in day.route_legs)
        expected_cost = sum(
            item.amount.amount for item in outcome.itinerary.budget.items if item.date == day.date
        )
        assert day.statistics.walking_meters == expected_walking
        assert day.statistics.estimated_cost.amount == expected_cost


def test_same_facts_generate_identical_result() -> None:
    facts = build_fixture_facts()
    planner = DeterministicPlanner()

    first = planner.plan(facts)
    second = planner.plan(facts)

    assert first == second
    assert first.itinerary.model_dump_json() == second.itinerary.model_dump_json()
    assert first.report.model_dump_json() == second.report.model_dump_json()


def test_accessible_required_unknown_place_returns_unsatisfied() -> None:
    facts = build_fixture_facts()
    request_data = facts.request.model_dump(mode="python")
    request_data["constraints"]["accessible_only"] = True
    request_data["constraints"]["required_place_names"] = ["三鹰之森吉卜力美术馆"]
    request = type(facts.request).model_validate(request_data)
    impossible_facts = type(facts)(
        request=request,
        places=facts.places,
        weather=facts.weather,
        route_matrix=facts.route_matrix,
        exchange_rates=facts.exchange_rates,
        planned_at=facts.planned_at,
    )

    outcome = DeterministicPlanner().plan(impossible_facts)

    assert outcome.status == PlanningStatus.UNSATISFIED
    assert outcome.report.passed is False
    assert any(item.code == "REQUIRED_PLACE_MISSING" for item in outcome.report.violations)
