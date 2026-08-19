from app.domain.itinerary import Itinerary
from app.fixtures.loader import (
    load_tokyo_places,
    load_tokyo_route_matrix,
    load_tokyo_trip_request,
    load_tokyo_weather,
)
from app.scripts.build_fixture_itinerary import build_blank_itinerary


def test_tokyo_fixture_is_internally_consistent() -> None:
    trip = load_tokyo_trip_request()
    weather = load_tokyo_weather()
    places = load_tokyo_places()
    matrix = load_tokyo_route_matrix()

    assert trip.date_range.day_count == 5
    assert trip.travelers == 2
    assert trip.constraints.total_budget.amount == 500_000
    assert trip.constraints.total_budget.currency == "CNY"

    expected_dates = {
        trip.date_range.start_date.fromordinal(trip.date_range.start_date.toordinal() + offset)
        for offset in range(trip.date_range.day_count)
    }
    assert {day.date for day in weather} == expected_dates
    assert len(weather) == 5
    assert any(day.outdoor_suitability == "poor" for day in weather)

    place_ids = {place.id for place in places}
    assert len(place_ids) == len(places)
    assert len(places) >= 10
    place_types = {place.indoor_outdoor for place in places}
    assert {"indoor", "outdoor", "mixed"} <= place_types
    assert any(place.reservation_required is True for place in places)
    assert any(period.closed for place in places for period in place.opening_periods)
    assert all(place.source is not None for place in places)

    assert 20 <= len(matrix.cells) <= 30

    for cell in matrix.cells:
        assert cell.origin_place_id in place_ids
        assert cell.destination_place_id in place_ids
        assert cell.origin_place_id != cell.destination_place_id
        if cell.status == "ok":
            assert cell.duration_minutes is not None
            assert cell.distance_meters is not None
            assert cell.walking_meters is not None


def test_blank_itinerary_covers_complete_trip() -> None:
    itinerary = build_blank_itinerary()

    assert len(itinerary.days) == 5
    assert [day.day_number for day in itinerary.days] == [1, 2, 3, 4, 5]
    assert all(day.activities == [] for day in itinerary.days)
    assert all(day.route_legs == [] for day in itinerary.days)
    assert all(day.statistics.activity_count == 0 for day in itinerary.days)
    assert itinerary.budget.planned_total.amount == 0
    assert itinerary.budget.remaining_amount == itinerary.budget.limit.amount

    serialized = itinerary.model_dump_json()
    assert Itinerary.model_validate_json(serialized) == itinerary
