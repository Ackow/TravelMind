from datetime import UTC, datetime

import pytest

from app.domain.common import Money
from app.domain.itinerary import ExchangeRate
from app.planning.money import MissingExchangeRateError, MoneyConverter
from app.planning.planner import build_budget_summary


def test_money_converter_rounds_to_nearest_smallest_unit() -> None:
    rate = ExchangeRate(
        from_currency="JPY",
        to_currency="CNY",
        rate=4.8,
        fetched_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    converter = MoneyConverter({"JPY/CNY": rate})

    assert converter.convert(Money(amount=101, currency="JPY"), "CNY") == Money(
        amount=485,
        currency="CNY",
    )


def test_money_converter_returns_same_currency_without_rate() -> None:
    money = Money(amount=100, currency="CNY")
    assert MoneyConverter({}).convert(money, "CNY") == money


def test_money_converter_rejects_missing_rate() -> None:
    with pytest.raises(MissingExchangeRateError, match="JPY/CNY"):
        MoneyConverter({}).convert(Money(amount=100, currency="JPY"), "CNY")


def test_budget_exactly_at_limit_is_allowed() -> None:
    """预算刚好用完时剩余金额为零，仍然属于预算内。"""
    summary = build_budget_summary(
        request_budget=Money(amount=0, currency="CNY"),
        items=[],
        exchange_rates={},
    )

    assert summary.remaining_amount == 0
    assert summary.within_budget is True
