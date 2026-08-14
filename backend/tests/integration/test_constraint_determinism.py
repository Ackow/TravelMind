from app.constraints import create_default_engine
from tests.integration.test_constraint_engine_tokyo import (
    build_conflicting_tokyo_itinerary,
    tokyo_context,
)


def test_same_conflicting_input_produces_identical_report() -> None:
    """包含真实违规时，两次检查的违规 ID、顺序和 JSON 必须完全一致。"""
    engine = create_default_engine()
    itinerary = build_conflicting_tokyo_itinerary()
    context = tokyo_context()

    first = engine.check(itinerary, context)
    second = engine.check(itinerary, context)

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert len({item.id for item in first.violations}) == len(first.violations)
