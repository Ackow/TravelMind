from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal

from app.domain.common import Money
from app.domain.itinerary import ExchangeRate


class MissingExchangeRateError(ValueError):
    """缺少必要汇率时抛出的明确错误。"""


class MoneyConverter:
    """把金额换算为行程展示币种。

    ExchangeRate.rate 在本项目中的精确定义是：
    “一个来源币种最小单位等于多少目标币种最小单位”。
    例如 JPY 没有角分，1 JPY 约等于 4.8 CNY 分，因此示例 rate=4.8。
    """

    def __init__(self, rates: Mapping[str, ExchangeRate]) -> None:
        self._rates = dict(rates)

    @staticmethod
    def rate_key(from_currency: str, to_currency: str) -> str:
        return f"{from_currency}/{to_currency}"

    def convert(self, money: Money, target_currency: str) -> Money:
        """使用十进制定点计算换算金额，避免二进制浮点误差。"""
        if money.currency == target_currency:
            return money

        key = self.rate_key(money.currency, target_currency)
        exchange_rate = self._rates.get(key)
        if exchange_rate is None:
            raise MissingExchangeRateError(f"missing exchange rate: {key}")

        converted = (Decimal(money.amount) * Decimal(str(exchange_rate.rate))).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )

        return Money(amount=int(converted), currency=target_currency)
