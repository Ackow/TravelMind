from app.constraints.engine import ConstraintEngine
from app.constraints.rules.activity_count import ActivityCountRule
from app.constraints.rules.budget import BudgetRule
from app.constraints.rules.daily_end_time import DailyEndTimeRule
from app.constraints.rules.date_range import DateRangeRule
from app.constraints.rules.opening_hours import OpeningHoursRule
from app.constraints.rules.overlap import ActivityOverlapRule
from app.constraints.rules.place_selection import ExcludedPlaceRule, RequiredPlaceRule
from app.constraints.rules.transfer import TransferRule
from app.constraints.rules.walking import WalkingLimitRule
from app.constraints.rules.weather import WeatherCompatibilityRule


def create_default_engine() -> ConstraintEngine:
    return ConstraintEngine(
        rules=(
            DateRangeRule(),
            ActivityOverlapRule(),
            ActivityCountRule(),
            BudgetRule(),
            DailyEndTimeRule(),
            OpeningHoursRule(),
            ExcludedPlaceRule(),
            RequiredPlaceRule(),
            TransferRule(),
            WalkingLimitRule(),
            WeatherCompatibilityRule(),
        )
    )
