from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext
from app.constraints.engine import ConstraintEngine
from app.constraints.violation_factory import make_violation
from app.domain.constraints import (
    ConstraintCode,
    ConstraintReport,
    ConstraintSeverity,
    ConstraintViolation,
)
from app.domain.itinerary import Itinerary
from app.fixtures.loader import load_tokyo_places, load_tokyo_trip_request
from app.scripts.build_fixture_itinerary import build_blank_itinerary


def tokyo_context() -> ConstraintContext:
    """为确定性测试提供固定的检查时间。"""
    places = load_tokyo_places()
    return ConstraintContext(
        request=load_tokyo_trip_request(),
        places_by_id={place.id: place for place in places},
        checked_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


@dataclass(frozen=True)
class FixedRule:
    """测试专用规则，只返回预先提供的固定违规记录。"""

    code: ConstraintCode
    violations: tuple[ConstraintViolation, ...] = ()
    version: str = "1.0.0"

    def check(
        self,
        itinerary: Itinerary,
        context: ConstraintContext,
    ) -> list[ConstraintViolation]:
        del itinerary, context
        return list(self.violations)


def fixed_violation(
    *,
    code: ConstraintCode,
    severity: ConstraintSeverity,
) -> ConstraintViolation:
    """构造 ID 稳定的引擎测试违规项。"""
    return make_violation(
        code=code,
        severity=severity,
        message="引擎测试违规",
        actual={"value": 2},
        expected={"value": 1},
        repair_hint="修复测试数据",
        rule_version="1.0.0",
    )


def test_engine_rejects_duplicate_rule_codes() -> None:
    """一个规则编码只能由一个注册规则负责。"""
    with pytest.raises(ValueError, match="codes must be unique"):
        ConstraintEngine(
            [
                FixedRule(ConstraintCode.ACTIVITY_OVERLAP),
                FixedRule(ConstraintCode.ACTIVITY_OVERLAP),
            ]
        )


def test_engine_runs_all_rules_when_filter_is_none() -> None:
    """未传筛选条件时必须运行全部注册规则。"""
    engine = ConstraintEngine(
        [
            FixedRule(ConstraintCode.DATE_OUT_OF_RANGE),
            FixedRule(ConstraintCode.ACTIVITY_OVERLAP),
        ]
    )

    report = engine.check(build_blank_itinerary(), tokyo_context())

    assert report.checked_rule_codes == [
        ConstraintCode.ACTIVITY_OVERLAP,
        ConstraintCode.DATE_OUT_OF_RANGE,
    ]
    assert report.checked_at == tokyo_context().checked_at


def test_engine_filters_rules_by_code() -> None:
    """显式筛选时只运行选中的规则。"""
    engine = ConstraintEngine(
        [
            FixedRule(ConstraintCode.DATE_OUT_OF_RANGE),
            FixedRule(ConstraintCode.ACTIVITY_OVERLAP),
        ]
    )

    report = engine.check(
        build_blank_itinerary(),
        tokyo_context(),
        rule_codes=[ConstraintCode.ACTIVITY_OVERLAP],
    )

    assert report.checked_rule_codes == [ConstraintCode.ACTIVITY_OVERLAP]


def test_engine_passes_when_only_warning_exists() -> None:
    """警告可以展示，但不能把报告的 passed 改成 False。"""
    warning = fixed_violation(
        code=ConstraintCode.WEATHER_MISMATCH,
        severity=ConstraintSeverity.WARNING,
    )
    report = ConstraintEngine([FixedRule(ConstraintCode.WEATHER_MISMATCH, (warning,))]).check(
        build_blank_itinerary(), tokyo_context()
    )

    assert report.passed is True
    assert [item.severity for item in report.violations] == [ConstraintSeverity.WARNING]


def test_engine_fails_and_sorts_errors_before_warnings() -> None:
    """只要存在错误就不通过，并按严重程度稳定排序。"""
    warning = fixed_violation(
        code=ConstraintCode.WEATHER_MISMATCH,
        severity=ConstraintSeverity.WARNING,
    )
    error = fixed_violation(
        code=ConstraintCode.ACTIVITY_OVERLAP,
        severity=ConstraintSeverity.ERROR,
    )
    report = ConstraintEngine(
        [
            FixedRule(ConstraintCode.WEATHER_MISMATCH, (warning,)),
            FixedRule(ConstraintCode.ACTIVITY_OVERLAP, (error,)),
        ]
    ).check(build_blank_itinerary(), tokyo_context())

    assert report.passed is False
    assert [item.severity for item in report.violations] == [
        ConstraintSeverity.ERROR,
        ConstraintSeverity.WARNING,
    ]


def test_default_engine_is_deterministic_and_does_not_modify_input() -> None:
    """同一输入产生完全相同的报告，同时不能修改原始行程。"""
    engine = create_default_engine()
    itinerary = build_blank_itinerary()
    original_json = itinerary.model_dump_json()
    context = tokyo_context()

    first = engine.check(itinerary, context)
    second = engine.check(itinerary, context)

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert itinerary.model_dump_json() == original_json
    assert ConstraintReport.model_validate_json(first.model_dump_json()) == first
