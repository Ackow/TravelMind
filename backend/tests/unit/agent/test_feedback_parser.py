from app.agent.feedback_parser import FeedbackParser, ParsedFeedback, SetMaxWalkingOp, AddExcludedPlaceOp
from app.agent.llm_client import FakeLLMClient
from app.fixtures.loader import load_tokyo_trip_request


def test_parser_extracts_walking_and_excluded_places() -> None:
    expected = ParsedFeedback(
        summary="用户希望减少步行并排除银座",
        operations=[
            SetMaxWalkingOp(op="set_max_walking", meters_per_day=3000, reason="减少步行"),
            AddExcludedPlaceOp(op="add_excluded_place", place_name="银座", reason="用户不想去"),
        ],
        affected_day_indices=[],
        requires_clarification=False,
    )
    fake_client = FakeLLMClient([expected])
    parser = FeedbackParser(fake_client)

    result = parser.parse("每天最多走 3 公里，不要去银座", load_tokyo_trip_request())

    assert len(result.operations) == 2
    assert result.operations[0].op == "set_max_walking"
    assert result.operations[0].meters_per_day == 3000
    assert result.operations[1].op == "add_excluded_place"
    assert result.operations[1].place_name == "银座"
    assert not result.requires_clarification