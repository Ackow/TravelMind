from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.common import DateRange, GeoPoint, Money


def test_money_accepts_smallest_currency_unit() -> None:
    money = Money(amount=10000, currency="JPY")

    assert money.amount == 10000
    assert money.currency == "JPY"


def test_money_rejects_invalid_currency() -> None:
    with pytest.raises(ValidationError):
        Money(amount=100, currency="rmb")


def test_domain_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Money.model_validate({"amount": 100, "currency": "CNY", "unknown": True})


@pytest.mark.parametrize("amount", [-1, -100])
def test_money_rejects_negative_amount(amount: int) -> None:
    with pytest.raises(ValidationError):
        Money(amount=amount, currency="CNY")


def test_geo_point_rejects_invalid_latitude() -> None:
    with pytest.raises(ValidationError):
        GeoPoint(latitude=91, longitude=139.7)


def test_date_range_rejects_reversed_dates() -> None:
    with pytest.raises(ValidationError):
        DateRange(
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 1),
        )


def test_date_range_counts_both_endpoints() -> None:
    value = DateRange(
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
    )

    assert value.day_count == 5
