from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.common import Money
from app.domain.itinerary import BudgetSummary, DayPlan, DayStatistics, Itinerary
from app.fixtures.loader import load_tokyo_trip_request, load_tokyo_weather

FIXTURE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")


def build_blank_itinerary() -> Itinerary:
    trip = load_tokyo_trip_request()
    weather_by_date = {item.date: item for item in load_tokyo_weather()}
    currency = trip.constraints.total_budget.currency

    days = []
    for offset in range(trip.date_range.day_count):
        current_date = trip.date_range.start_date + timedelta(days=offset)
        days.append(
            DayPlan(
                date=current_date,
                day_number=offset + 1,
                theme="待规划",
                weather=weather_by_date.get(current_date),
                activities=[],
                route_legs=[],
                statistics=DayStatistics(estimated_cost=Money(amount=0, currency=currency)),
                warnings=[],
            )
        )

    return Itinerary(
        trip_id=FIXTURE_TRIP_ID,
        title=f"{trip.destination} {trip.date_range.day_count} 日游",
        destination=trip.destination,
        timezone=trip.destination_timezone,
        date_range=trip.date_range,
        days=days,
        budget=BudgetSummary(
            limit=trip.constraints.total_budget,
            planned_total=Money(amount=0, currency=currency),
            remaining_amount=trip.constraints.total_budget.amount,
            currency=currency,
            within_budget=True,
        ),
        general_notes=["这是阶段 1 生成的空白行程骨架"],
        generated_at=datetime.now(UTC),
    )


def main() -> None:
    itinerary = build_blank_itinerary()
    print(itinerary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
