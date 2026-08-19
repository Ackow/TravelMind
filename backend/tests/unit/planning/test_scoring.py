from app.planning.money import MoneyConverter
from app.planning.scoring import is_eligible, score_place
from app.scripts.generate_fixture_plan import build_fixture_facts


def test_culture_interest_increases_culture_place_score() -> None:
    facts = build_fixture_facts()
    places = {place.id: place for place in facts.places}
    weather = facts.weather[0]
    converter = MoneyConverter(facts.exchange_rates)

    culture = score_place(
        place=places["tm_place_nanjing_museum"],
        request=facts.request,
        weather=weather,
        converter=converter,
    )
    park = score_place(
        place=places["tm_place_xuanwu_lake"],
        request=facts.request,
        weather=weather,
        converter=converter,
    )

    assert culture.score > park.score
    assert any("文化" in reason or "历史" in reason for reason in culture.reasons)


def test_poor_weather_filters_outdoor_place() -> None:
    facts = build_fixture_facts()
    places = {place.id: place for place in facts.places}
    poor_weather = next(item for item in facts.weather if item.outdoor_suitability == "poor")

    assert (
        is_eligible(
            places["tm_place_fuzimiao"],
            facts.request,
            poor_weather,
        )
        is False
    )
    assert (
        is_eligible(
            places["tm_place_nanjing_museum"],
            facts.request,
            poor_weather,
        )
        is True
    )
