from app.planning.money import MoneyConverter
from app.planning.scoring import is_eligible, score_place
from app.scripts.generate_fixture_plan import build_fixture_facts


def test_anime_interest_increases_anime_place_score() -> None:
    facts = build_fixture_facts()
    places = {place.id: place for place in facts.places}
    weather = facts.weather[0]
    converter = MoneyConverter(facts.exchange_rates)

    anime = score_place(
        place=places["tm_place_akihabara"],
        request=facts.request,
        weather=weather,
        converter=converter,
    )
    park = score_place(
        place=places["tm_place_ueno_park"],
        request=facts.request,
        weather=weather,
        converter=converter,
    )

    assert anime.score > park.score
    assert any("动漫" in reason for reason in anime.reasons)


def test_poor_weather_filters_outdoor_place() -> None:
    facts = build_fixture_facts()
    places = {place.id: place for place in facts.places}
    poor_weather = next(item for item in facts.weather if item.outdoor_suitability == "poor")

    assert (
        is_eligible(
            places["tm_place_sensoji"],
            facts.request,
            poor_weather,
        )
        is False
    )
    assert (
        is_eligible(
            places["tm_place_tokyo_national_museum"],
            facts.request,
            poor_weather,
        )
        is True
    )
