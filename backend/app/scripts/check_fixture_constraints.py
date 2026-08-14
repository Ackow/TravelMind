from datetime import UTC, datetime

from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.fixtures.loader import load_tokyo_places, load_tokyo_trip_request
from app.scripts.build_fixture_itinerary import build_blank_itinerary


def main() -> None:
    """检查东京空白行程，并将可回读的约束报告 JSON 输出到终端。"""
    places = load_tokyo_places()
    context = ConstraintContext(
        request=load_tokyo_trip_request(),
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    report = create_default_engine().check(
        itinerary=build_blank_itinerary(),
        context=context,
    )
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
