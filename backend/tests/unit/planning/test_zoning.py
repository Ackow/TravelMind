from app.planning.zoning import build_zones
from app.scripts.generate_fixture_plan import build_fixture_facts


def test_zoning_covers_each_place_exactly_once() -> None:
    facts = build_fixture_facts()
    zones = build_zones(
        places=facts.places,
        route_matrix=facts.route_matrix,
        target_zone_count=5,
    )

    zone_place_ids = [place_id for zone in zones for place_id in zone.place_ids]
    assert len(zones) == 5
    assert sorted(zone_place_ids) == sorted(place.id for place in facts.places)
    assert len(zone_place_ids) == len(set(zone_place_ids))


def test_zoning_is_deterministic() -> None:
    facts = build_fixture_facts()
    first = build_zones(
        places=facts.places,
        route_matrix=facts.route_matrix,
        target_zone_count=5,
    )
    second = build_zones(
        places=tuple(reversed(facts.places)),
        route_matrix=facts.route_matrix,
        target_zone_count=5,
    )

    assert first == second
