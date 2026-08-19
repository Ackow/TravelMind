from datetime import date

from app.domain.common import DateRange, Money
from app.domain.trip import (
    Pace,
    TransportMode,
    TripConstraints,
    TripPreferences,
    TripRequest,
    WeightedPreference,
)
from app.eval.models import EvalExpectation, GoldenEvalCase


def get_golden_dataset() -> list[GoldenEvalCase]:
    """获取覆盖全维度的标准黄金评测数据集（以 杭州 -> 南京 作为基准基线）。"""
    cases: list[GoldenEvalCase] = []

    # 1. 常规标准旅行场景 (Standard Trips)
    cases.append(
        GoldenEvalCase(
            case_id="TC_001_STD_3D",
            category="standard",
            title="南京 3 日经典游",
            description="标准 2 人均衡节奏文化游",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 3)),
                travelers=2,
                preferences=TripPreferences(
                    pace=Pace.BALANCED,
                    interests=[WeightedPreference(value="文化古迹", weight=0.9)],
                    transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
                ),
                constraints=TripConstraints(
                    total_budget=Money(amount=400000, currency="CNY"),
                    max_walking_meters_per_day=10000,
                    daily_start_time="09:00",
                    daily_end_time="20:00",
                ),
                display_currency="CNY",
            ),
            expectations=EvalExpectation(must_pass_constraints=True, max_days=3),
        )
    )

    # 2. 5 日深度游
    cases.append(
        GoldenEvalCase(
            case_id="TC_002_STD_5D",
            category="standard",
            title="南京 5 日深度游",
            description="标准 5 日游览南京主城区经典地标",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 5)),
                travelers=2,
                preferences=TripPreferences(pace=Pace.BALANCED),
                constraints=TripConstraints(
                    total_budget=Money(amount=600000, currency="CNY"),
                    max_walking_meters_per_day=12000,
                    daily_start_time="09:00",
                    daily_end_time="20:00",
                ),
                display_currency="CNY",
            ),
            expectations=EvalExpectation(must_pass_constraints=True, max_days=5),
        )
    )

    # 3. 恶劣天气与暴雨避险场景 (Weather Stress)
    cases.append(
        GoldenEvalCase(
            case_id="TC_003_RAIN_STRESS",
            category="weather_stress",
            title="连续雨天室内替换",
            description="测试在雨天是否自动将户外公园置换为博物馆/咖啡馆/购物中心",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 3)),
                travelers=2,
                preferences=TripPreferences(pace=Pace.BALANCED),
                constraints=TripConstraints(
                    total_budget=Money(amount=300000, currency="CNY"),
                    max_walking_meters_per_day=8000,
                    daily_start_time="09:30",
                    daily_end_time="19:30",
                ),
                display_currency="CNY",
            ),
            expectations=EvalExpectation(must_pass_constraints=True),
        )
    )

    # 4. 周一闭馆冲突场景 (Museum Closure Stress)
    cases.append(
        GoldenEvalCase(
            case_id="TC_004_CLOSURE_STRESS",
            category="closure_stress",
            title="周一闭馆自动避开",
            description="行程跨越周一，包含周一闭馆的南京博物院与中山陵，测试规则引擎与规划器自动调期",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 4), end_date=date(2026, 10, 6)),
                travelers=2,
                preferences=TripPreferences(pace=Pace.BALANCED),
                constraints=TripConstraints(
                    total_budget=Money(amount=500000, currency="CNY"),
                    max_walking_meters_per_day=10000,
                    daily_start_time="09:00",
                    daily_end_time="20:00",
                ),
                display_currency="CNY",
            ),
            expectations=EvalExpectation(must_pass_constraints=True),
        )
    )

    # 5. 局部动态重规划保留率场景 (Replanning Stability)
    cases.append(
        GoldenEvalCase(
            case_id="TC_005_REPLAN_SCOPED",
            category="replanning",
            title="只修改第二天的局部重排",
            description="初始生成 5 天方案后，用户提出修改第 2 天，测试其余 4 天活动保持不变",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 5)),
                travelers=2,
                preferences=TripPreferences(pace=Pace.BALANCED),
                constraints=TripConstraints(
                    total_budget=Money(amount=500000, currency="CNY"),
                    max_walking_meters_per_day=10000,
                    daily_start_time="09:00",
                    daily_end_time="20:00",
                ),
                display_currency="CNY",
            ),
            feedback="第二天下午我想在老门东和新街口多休息，不要走太多路",
            expectations=EvalExpectation(must_pass_constraints=True),
        )
    )

    # 6. 相互冲突无解诉求拒识场景 (Unfeasible Rejection)
    cases.append(
        GoldenEvalCase(
            case_id="TC_006_UNFEASIBLE_CONFLICT",
            category="unfeasible",
            title="冲突需求识别与拒绝",
            description="每日作息仅允许 1 小时 (09:00~10:00) 却要求游览大量景点，预期系统正确拒识",
            request=TripRequest(
                origin="杭州",
                destination="南京",
                destination_timezone="Asia/Shanghai",
                date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 3)),
                travelers=1,
                preferences=TripPreferences(pace=Pace.PACKED),
                constraints=TripConstraints(
                    total_budget=Money(amount=5000, currency="CNY"),
                    max_walking_meters_per_day=2000,
                    daily_start_time="09:00",
                    daily_end_time="10:00",
                ),
                display_currency="CNY",
            ),
            expectations=EvalExpectation(must_pass_constraints=False, expected_unfeasible=True),
        )
    )

    return cases
