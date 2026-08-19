"""TravelMind 演示数据种子生成脚本。

严格按照业务要求写入两条真实数据：
1. 方案一（南京 5 日游 `77777777-7777-7777-7777-777777777777`）：经历 3 个版本迭代（v1 -> v2 -> v3）后最终确认（completed）。
2. 方案二（北京 4 日游 `99999999-9999-9999-9999-999999999999`）：阶段 1 初次规划草案阶段（needs_review）。

所有日程均以真实酒店/火车站交通枢纽为起始与结束点，行程间包含地铁几号线换乘与站点出口等精确交通方式。
推荐的所有饭店、酒店与景点均为真实存在且可在地图精确定位的实体。
"""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

CST = timezone(timedelta(hours=8))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保脚本能正确导入 app 模块
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningEventType,
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripRecord,
    TripStatus,
)
from app.core.config import get_settings
from app.domain.common import DateRange, Money, SourceRef
from app.domain.constraints import ConstraintCode, ConstraintReport
from app.domain.itinerary import (
    Activity,
    ActivityKind,
    ActivitySourceType,
    BudgetCategory,
    BudgetItem,
    BudgetSummary,
    DayPlan,
    DayStatistics,
    IndoorOutdoor,
    Itinerary,
    RouteLeg,
)
from app.domain.research import OutdoorSuitability, WeatherCondition, WeatherDay
from app.domain.trip import (
    Pace,
    TransportMode,
    TripConstraints,
    TripPreferences,
    TripRequest,
    WeightedPreference,
)
from app.infrastructure.sql_repository import SqlAlchemyTravelRepository
from app.persistence.base import Base


def _build_source(name: str) -> SourceRef:
    return SourceRef(
        provider="amap",
        source_id=name,
        source_url=f"https://www.amap.com/place/{name}",
        fetched_at=datetime(2026, 9, 30, 0, 0, 0, tzinfo=CST),
        expires_at=datetime(2026, 12, 31, 0, 0, 0, tzinfo=CST),
        data_quality="verified",
    )


def _build_weather(d: date, cond: WeatherCondition, min_c: float, max_c: float, rain_prob: float = 0.0) -> WeatherDay:
    return WeatherDay(
        date=d,
        condition=cond,
        temperature_min_c=min_c,
        temperature_max_c=max_c,
        rain_probability=rain_prob,
        outdoor_suitability=OutdoorSuitability.GOOD if cond == WeatherCondition.CLEAR else OutdoorSuitability.ACCEPTABLE,
        source=_build_source("CMAWeather"),
    )


def _build_budget_summary(limit_amount: int, items_def: list[tuple[BudgetCategory, str, int]]) -> BudgetSummary:
    items: list[BudgetItem] = []
    totals_by_cat: dict[BudgetCategory, int] = {}
    for i, (cat, label, amt) in enumerate(items_def):
        items.append(
            BudgetItem(
                id=UUID(f"00000000-0000-0000-0000-{i+1:012d}"),
                category=cat,
                label=label,
                date=None,
                activity_id=None,
                amount=Money(amount=amt, currency="CNY"),
                estimated=True,
                source=_build_source("BudgetEstimator"),
            )
        )
        totals_by_cat[cat] = totals_by_cat.get(cat, 0) + amt

    planned_cents = sum(item.amount.amount for item in items)
    rem = limit_amount - planned_cents
    return BudgetSummary(
        limit=Money(amount=limit_amount, currency="CNY"),
        items=items,
        totals_by_category={k: Money(amount=v, currency="CNY") for k, v in totals_by_cat.items()},
        planned_total=Money(amount=planned_cents, currency="CNY"),
        remaining_amount=rem,
        currency="CNY",
        within_budget=rem >= 0,
        exchange_rates={},
    )


# ==========================================
# 方案 1：南京 5 日游（3 个版本迭代后确认）
# ==========================================
def create_nanjing_trip_and_versions(now: datetime) -> tuple[TripRecord, list[PlanVersionRecord], list[PlanningRunRecord], list[PlanningEventRecord], list[FeedbackRecord]]:
    trip_id = UUID("77777777-7777-7777-7777-777777777777")
    run_id_v1 = UUID("77777777-0001-0000-0000-000000000001")
    run_id_v2 = UUID("77777777-0002-0000-0000-000000000002")
    run_id_v3 = UUID("77777777-0003-0000-0000-000000000003")

    plan_id_v1 = UUID("77777777-0001-0001-0001-000100010001")
    plan_id_v2 = UUID("77777777-0002-0002-0002-000200020002")
    plan_id_v3 = UUID("77777777-0003-0003-0003-000300030003")

    feedback_id_1 = UUID("77777777-0002-0000-0000-000000000001")
    feedback_id_2 = UUID("77777777-0003-0000-0000-000000000001")

    # 1. 旅行请求模型
    request = TripRequest(
        origin="杭州",
        destination="南京",
        destination_timezone="Asia/Shanghai",
        date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 5)),
        travelers=2,
        preferences=TripPreferences(
            interests=[
                WeightedPreference(value="文化古迹", weight=0.9),
                WeightedPreference(value="特色美食", weight=0.8),
                WeightedPreference(value="城市漫步", weight=0.7),
            ],
            avoid=[],
            dietary=[],
            transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
            accommodation_notes="入住金陵饭店(新街口店)，靠近地铁1/2号线新街口枢纽站",
            pace=Pace.BALANCED,
            must_visit_place_names=["南京博物院", "夫子庙-秦淮风光带", "中山陵景区"],
        ),
        constraints=TripConstraints(
            total_budget=Money(amount=800000, currency="CNY"),
            budget_is_hard_limit=True,
            daily_start_time="09:00",
            daily_end_time="21:00",
            max_walking_meters_per_day=10000,
            max_activities_per_day=6,
            minimum_transfer_buffer_minutes=10,
            rest_minutes_per_day=60,
            required_place_names=["南京博物院", "夫子庙-秦淮风光带", "中山陵景区"],
            excluded_place_names=[],
            accessible_only=False,
        ),
        locale="zh-CN",
        display_currency="CNY",
        notes="从杭州东站乘高铁抵达南京南站，全程以金陵饭店为大本营，要求详细的地铁换乘与真实餐饮安排。",
    )

    trip = TripRecord(
        id=trip_id,
        status=TripStatus.COMPLETED,
        revision=3,
        request=request,
        current_plan_version=3,
        active_planning_run_id=None,
        created_at=now,
        updated_at=now,
    )

    # 2. 规划任务记录 v1, v2, v3
    run_v1 = PlanningRunRecord(
        id=run_id_v1,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.INITIAL,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=None,
        result_plan_version=1,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )

    run_v2 = PlanningRunRecord(
        id=run_id_v2,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.FEEDBACK,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=1,
        result_plan_version=2,
        feedback_id=feedback_id_1,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )

    run_v3 = PlanningRunRecord(
        id=run_id_v3,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.FEEDBACK,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=2,
        result_plan_version=3,
        feedback_id=feedback_id_2,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )

    # 3. 用户反馈记录
    fb_1 = FeedbackRecord(
        id=feedback_id_1,
        trip_id=trip_id,
        base_plan_version=1,
        message="Day 2 调整为 10:30 晚出发，并在傍晚安排玄武湖公园日落与湖畔特色淮扬菜",
        operations=[
            {"op": "shift_start_time", "day_number": 2, "new_start_time": "10:30", "reason": "配合用户晚出发偏好"},
            {"op": "add_activity", "day_number": 2, "place_name": "玄武湖公园", "time": "17:00"},
        ],
        affected_dates=[date(2026, 10, 2)],
        affected_activity_ids=[],
        global_scope=False,
        requires_clarification=False,
        clarification_question=None,
        planning_run_id=run_id_v2,
        created_at=now,
    )

    fb_2 = FeedbackRecord(
        id=feedback_id_2,
        trip_id=trip_id,
        base_plan_version=2,
        message="将每日最大步行距离收紧至 8 km，并在钟山与玄武湖增加点对点接驳观光车与地铁直达",
        operations=[
            {"op": "set_max_walking", "meters_per_day": 8000, "reason": "降低长辈出行步行负荷"},
            {"op": "add_transit_transfer", "day_number": 2, "mode": "观光车", "reason": "钟山风景名胜区观光车接驳"},
        ],
        affected_dates=[],
        affected_activity_ids=[],
        global_scope=True,
        requires_clarification=False,
        clarification_question=None,
        planning_run_id=run_id_v3,
        created_at=now,
    )

    # 4. 构建真实 5 日行程
    def build_nanjing_days(version: int) -> list[DayPlan]:
        days: list[DayPlan] = []

        # ---------- Day 1: 抵达金陵、入住新街口、总统府与夜游秦淮 ----------
        d1_date = date(2026, 10, 1)
        r1_leg1_id = UUID(f"77777777-100{version}-0001-0000-000000000001")
        r1_leg1 = RouteLeg(
            id=r1_leg1_id,
            origin_place_id="tm_place_nanjing_south_station",
            destination_place_id="tm_place_jinling_hotel",
            mode=TransportMode.PUBLIC_TRANSIT,
            departure_time=datetime(2026, 10, 1, 9, 0, 0, tzinfo=CST),
            arrival_time=datetime(2026, 10, 1, 9, 30, 0, tzinfo=CST),
            duration_minutes=30,
            distance_meters=8500,
            walking_meters=350,
            cost=Money(amount=400, currency="CNY"),
            instructions_summary="地铁1号线 (南京南站→新街口站，耗时约18分钟，6号口出步行150米至酒店大堂)",
            source=_build_source("AmapRouteMatrix"),
        )
        d1_acts = [
            Activity(
                id=UUID(f"77777777-000{version}-0101-0000-000000000001"),
                kind=ActivityKind.TRANSFER,
                title="抵达南京南站并搭乘地铁1号线",
                place_id="tm_place_nanjing_south_station",
                start_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 9, 30, 0, tzinfo=CST),
                route_leg_id=r1_leg1_id,
                estimated_cost=Money(amount=800, currency="CNY"),
                priority=100,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="高铁抵达南京南站，开启行程",
                notes=["地铁1号线 (南京南站→新街口站，约18分钟，6号口出)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0102-0000-000000000002"),
                kind=ActivityKind.CHECK_IN,
                title="金陵饭店(新街口店) 办理入住与行李寄存",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 1, 9, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 10, 15, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="新街口核心商圈五星级大本营，出入双地铁极便",
                notes=["新街口站6号口直通饭店大堂，前台办理快速入住并寄存行李"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0103-0000-000000000003"),
                kind=ActivityKind.VISIT,
                title="南京总统府",
                place_id="tm_place_presidential_palace",
                start_at=datetime(2026, 10, 1, 10, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 12, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=7000, currency="CNY"),
                priority=80,
                locked=False,
                indoor_outdoor=IndoorOutdoor.MIXED,
                reason="中国近代历史重要遗存，民国建筑群",
                notes=["地铁2号线 (新街口站→大行宫站，约5分钟，5号口出步行200米)", "需提前在线预约实名门票"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0104-0000-000000000004"),
                kind=ActivityKind.MEAL,
                title="民国往事·民国红公馆(1912街区店)",
                place_id="tm_place_honggongguan",
                start_at=datetime(2026, 10, 1, 12, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 13, 45, 0, tzinfo=CST),
                estimated_cost=Money(amount=28000, currency="CNY"),
                priority=70,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="总统府旁1912街区，品味地道民国官府菜与精致淮扬点心",
                notes=["从总统府东门步行约250米即达1912街区太平北路入口"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0105-0000-000000000005"),
                kind=ActivityKind.VISIT,
                title="南京博物院 (历史馆与特展馆)",
                place_id="tm_place_nanjing_museum",
                start_at=datetime(2026, 10, 1, 14, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 17, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=95,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="中国三大博物馆之一，重磅必去文化地标",
                notes=["地铁2号线 (大行宫站→明故宫站，约6分钟，1号口出步行350米)", "门票免费但需提前7天预约"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0106-0000-000000000006"),
                kind=ActivityKind.VISIT,
                title="夫子庙-秦淮风光带 & 秦淮画舫",
                place_id="tm_place_fuzimiao",
                start_at=datetime(2026, 10, 1, 17, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 19, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=16000, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.OUTDOOR,
                reason="十里秦淮十里风光，江南贡院与夜游游船",
                notes=["地铁2号线转3号线 (明故宫站→大行宫站换乘3号线→夫子庙站，约16分钟，3号口出)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0107-0000-000000000007"),
                kind=ActivityKind.MEAL,
                title="南京大牌档(德基广场店)",
                place_id="tm_place_nanjing_dapaidang",
                start_at=datetime(2026, 10, 1, 19, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 20, 45, 0, tzinfo=CST),
                estimated_cost=Money(amount=18000, currency="CNY"),
                priority=60,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="品尝美龄粥、金牌烤鸭、民国美点等金陵风味",
                notes=["地铁3号线转1号线 (夫子庙站→新街口站，约12分钟，7号口出直通德基广场一期7F)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0108-0000-000000000008"),
                kind=ActivityKind.REST,
                title="返回金陵饭店(新街口店) 休息",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 1, 21, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 1, 21, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="结束第一日充实旅程，回到饭店安歇",
                notes=["从德基广场地下商道步行约4分钟直接返回金陵饭店"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
        ]
        days.append(
            DayPlan(
                date=d1_date,
                day_number=1,
                theme="抵宁安顿、六朝文脉与夜泊秦淮",
                weather=_build_weather(d1_date, WeatherCondition.CLEAR, 18.0, 25.0, 0.05),
                activities=d1_acts,
                route_legs=[r1_leg1],
                statistics=DayStatistics(activity_count=8, walking_meters=4800, transfer_minutes=68, planned_minutes=480, estimated_cost=Money(amount=69800, currency="CNY")),
                warnings=["国庆黄金周期间南京博物院与秦淮画舫人流密集，请提前凭身份证原件验票。"],
            )
        )

        # ---------- Day 2: 钟山胜境、古鸡鸣寺与玄武湖日落 ----------
        d2_date = date(2026, 10, 2)
        d2_start = datetime(2026, 10, 2, 10, 30, 0, tzinfo=CST) if version >= 2 else datetime(2026, 10, 2, 9, 0, 0, tzinfo=CST)
        d2_leg1_end = d2_start + timedelta(minutes=30)
        d2_visit1_end = d2_leg1_end + timedelta(hours=2)

        r2_leg1_id = UUID(f"77777777-200{version}-0001-0000-000000000001")
        r2_leg1 = RouteLeg(
            id=r2_leg1_id,
            origin_place_id="tm_place_jinling_hotel",
            destination_place_id="tm_place_zhongshan_ling",
            mode=TransportMode.PUBLIC_TRANSIT,
            departure_time=d2_start,
            arrival_time=d2_leg1_end,
            duration_minutes=30,
            distance_meters=9200,
            walking_meters=400,
            cost=Money(amount=300, currency="CNY"),
            instructions_summary="地铁2号线 (新街口站→苜蓿园站，约15分钟，2号口出转景区观光车)",
            source=_build_source("AmapRouteMatrix"),
        )

        d2_acts = [
            Activity(
                id=UUID(f"77777777-000{version}-0201-0000-000000000001"),
                kind=ActivityKind.TRANSFER,
                title="金陵饭店(新街口店) 出发搭乘地铁2号线前往钟山",
                place_id="tm_place_jinling_hotel",
                start_at=d2_start,
                end_at=d2_leg1_end,
                route_leg_id=r2_leg1_id,
                estimated_cost=Money(amount=600, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="清晨出发前往钟山风景区",
                notes=["地铁2号线 (新街口站→苜蓿园站，约15分钟，2号口出转景区观光车)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0202-0000-000000000002"),
                kind=ActivityKind.VISIT,
                title="中山陵景区 & 音乐台",
                place_id="tm_place_zhongshan_ling",
                start_at=d2_leg1_end,
                end_at=d2_visit1_end,
                estimated_cost=Money(amount=2000, currency="CNY"),
                priority=95,
                locked=True,
                indoor_outdoor=IndoorOutdoor.OUTDOOR,
                reason="孙中山先生陵寝，庄严肃穆，音乐台群鸽翻飞",
                notes=["钟山风景区观光车1号线接驳，提前微信小程序预约入园凭证"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0203-0000-000000000003"),
                kind=ActivityKind.MEAL,
                title="南京大牌档 / 钟山特色雅致午餐",
                place_id="tm_place_xinjiekou",
                start_at=datetime(2026, 10, 2, 13, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 2, 14, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=16000, currency="CNY"),
                priority=60,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="景区适度休息，补充能量",
                notes=["景区观光车接驳至下马坊/苜蓿园站"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0204-0000-000000000004"),
                kind=ActivityKind.VISIT,
                title="古鸡鸣寺",
                place_id="tm_place_jiming_temple",
                start_at=datetime(2026, 10, 2, 14, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 2, 16, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=2000, currency="CNY"),
                priority=85,
                locked=False,
                indoor_outdoor=IndoorOutdoor.OUTDOOR,
                reason="南朝第一寺，登药师佛塔俯瞰玄武湖",
                notes=["地铁2号线转3号线 (苜蓿园站→大行宫站换乘3号线→鸡鸣寺站，约20分钟，4号口出)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0205-0000-000000000005"),
                kind=ActivityKind.VISIT,
                title="玄武湖公园 (环洲与梁洲日落游船)",
                place_id="tm_place_xuanwu_lake",
                start_at=datetime(2026, 10, 2, 16, 45, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 2, 19, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=12000, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.OUTDOOR,
                reason="从鸡鸣寺解放门直接穿入明城墙，饱览山水城林夕阳胜景",
                notes=["从古鸡鸣寺解放门台阶直接进入玄武湖，沿湖畔漫步与体验自驾游船"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0206-0000-000000000006"),
                kind=ActivityKind.MEAL,
                title="江南灶中餐厅(香格里拉大酒店)",
                place_id="tm_place_jiangnanzao",
                start_at=datetime(2026, 10, 2, 19, 15, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 2, 20, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=32000, currency="CNY"),
                priority=75,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="黑珍珠淮扬名菜，侯师傅精烹红烧肉与清汤狮子头",
                notes=["地铁1号线 (玄武门站→新模范马路站，约4分钟，1号口出步行300米)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0207-0000-000000000007"),
                kind=ActivityKind.REST,
                title="返回金陵饭店(新街口店) 休息",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 2, 20, 45, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 2, 21, 15, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="舒适返回酒店大本营休息",
                notes=["地铁1号线 (新模范马路站→新街口站，约8分钟，6号口出直通饭店)"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
        ]
        walking_d2 = 4200 if version == 3 else 5600
        days.append(
            DayPlan(
                date=d2_date,
                day_number=2,
                theme="钟山林海、古寺钟声与金陵明珠",
                weather=_build_weather(d2_date, WeatherCondition.CLEAR, 17.0, 24.0, 0.0),
                activities=d2_acts,
                route_legs=[r2_leg1],
                statistics=DayStatistics(activity_count=7, walking_meters=walking_d2, transfer_minutes=55, planned_minutes=460, estimated_cost=Money(amount=64600, currency="CNY")),
                warnings=[],
            )
        )

        # ---------- Day 3: 铭记历史、老门东老城南与非遗淮扬菜 ----------
        d3_date = date(2026, 10, 3)
        r3_leg1_id = UUID(f"77777777-300{version}-0001-0000-000000000001")
        r3_leg1 = RouteLeg(
            id=r3_leg1_id,
            origin_place_id="tm_place_jinling_hotel",
            destination_place_id="tm_place_memorial_hall",
            mode=TransportMode.PUBLIC_TRANSIT,
            departure_time=datetime(2026, 10, 3, 9, 0, 0, tzinfo=CST),
            arrival_time=datetime(2026, 10, 3, 9, 30, 0, tzinfo=CST),
            duration_minutes=30,
            distance_meters=5500,
            walking_meters=250,
            cost=Money(amount=300, currency="CNY"),
            instructions_summary="地铁2号线 (新街口站→云锦路站，约12分钟，2号口出步行200米)",
            source=_build_source("AmapRouteMatrix"),
        )
        d3_acts = [
            Activity(
                id=UUID(f"77777777-000{version}-0301-0000-000000000001"),
                kind=ActivityKind.TRANSFER,
                title="金陵饭店(新街口店) 出发前往纪念馆",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 3, 9, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 9, 30, 0, tzinfo=CST),
                route_leg_id=r3_leg1_id,
                estimated_cost=Money(amount=400, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="搭乘地铁2号线西行",
                notes=["地铁2号线 (新街口站→云锦路站，约12分钟，2号口出步行200米)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0302-0000-000000000002"),
                kind=ActivityKind.VISIT,
                title="侵华日军南京大屠杀遇难同胞纪念馆",
                place_id="tm_place_memorial_hall",
                start_at=datetime(2026, 10, 3, 9, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 12, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=95,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="铭记历史，珍爱和平，沉浸式爱国主义教育基地",
                notes=["提前7天实名预约，馆内需保持安静肃穆，建议参观2.5小时"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0303-0000-000000000003"),
                kind=ActivityKind.MEAL,
                title="绿柳居清真菜馆(太平南路总店)",
                place_id="tm_place_xinjiekou",
                start_at=datetime(2026, 10, 3, 12, 15, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 13, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=16000, currency="CNY"),
                priority=65,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="中华老字号，素菜包、盐水鸭与牛肉锅贴",
                notes=["地铁2号线转3号线 (云锦路站→大行宫站换乘3号线→常府街站，约18分钟，1号口出)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0304-0000-000000000004"),
                kind=ActivityKind.VISIT,
                title="老门东历史街区 & 芥子园",
                place_id="tm_place_laomendong",
                start_at=datetime(2026, 10, 3, 14, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 17, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=4000, currency="CNY"),
                priority=85,
                locked=False,
                indoor_outdoor=IndoorOutdoor.MIXED,
                reason="保留明清民居建筑风貌，手作非遗、古树石桥与芥子园微缩江南园林",
                notes=["地铁3号线 (常府街站→武定门站，约6分钟，2号口出步行400米进入老门东牌坊)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0305-0000-000000000005"),
                kind=ActivityKind.MEAL,
                title="小厨娘淮扬菜(老门东店)",
                place_id="tm_place_xiaochuniang",
                start_at=datetime(2026, 10, 3, 17, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 19, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=26000, currency="CNY"),
                priority=70,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="老门东三条营古色古香独栋院落，品尝软兜长鱼与鸡煲",
                notes=["位于老门东街区三条营49号，建议提前大众点评排号"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0306-0000-000000000006"),
                kind=ActivityKind.REST,
                title="返回金陵饭店(新街口店) 休息",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 3, 20, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 3, 20, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="乘地铁返回酒店休息",
                notes=["地铁3号线转1号线 (武定门站→大行宫站换乘2号线/1号线→新街口站，约15分钟)"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
        ]
        days.append(
            DayPlan(
                date=d3_date,
                day_number=3,
                theme="和平丰碑与老城南街巷市井",
                weather=_build_weather(d3_date, WeatherCondition.CLOUDY, 16.0, 23.0, 0.1),
                activities=d3_acts,
                route_legs=[r3_leg1],
                statistics=DayStatistics(activity_count=6, walking_meters=4500, transfer_minutes=50, planned_minutes=420, estimated_cost=Money(amount=46400, currency="CNY")),
                warnings=[],
            )
        )

        # ---------- Day 4: 金陵盛景牛首山与先锋书店人文漫步 ----------
        d4_date = date(2026, 10, 4)
        r4_leg1_id = UUID(f"77777777-400{version}-0001-0000-000000000001")
        r4_leg1 = RouteLeg(
            id=r4_leg1_id,
            origin_place_id="tm_place_jinling_hotel",
            destination_place_id="tm_place_niushoushan",
            mode=TransportMode.PUBLIC_TRANSIT,
            departure_time=datetime(2026, 10, 4, 9, 0, 0, tzinfo=CST),
            arrival_time=datetime(2026, 10, 4, 10, 0, 0, tzinfo=CST),
            duration_minutes=60,
            distance_meters=22000,
            walking_meters=350,
            cost=Money(amount=500, currency="CNY"),
            instructions_summary="地铁1号线转G70公交 (新街口站→天元西路站转G70至牛首山东门，约50分钟)",
            source=_build_source("AmapRouteMatrix"),
        )
        d4_acts = [
            Activity(
                id=UUID(f"77777777-000{version}-0401-0000-000000000001"),
                kind=ActivityKind.TRANSFER,
                title="金陵饭店(新街口店) 出发前往牛首山",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 4, 9, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 10, 0, 0, tzinfo=CST),
                route_leg_id=r4_leg1_id,
                estimated_cost=Money(amount=1200, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="地铁1号线转G70直达牛首山景区",
                notes=["地铁1号线 (新街口站→天元西路站，换乘G70路公交直通牛首山景区东门，约50分钟)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0402-0000-000000000002"),
                kind=ActivityKind.VISIT,
                title="牛首山文化旅游区 (佛顶宫与佛顶塔)",
                place_id="tm_place_niushoushan",
                start_at=datetime(2026, 10, 4, 10, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 14, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=29000, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="补天阙修圣境，世界级佛教艺术地下殿堂",
                notes=["景区门票 ¥145/人，内含观光车接驳，佛顶宫万佛廊深度参观"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0403-0000-000000000003"),
                kind=ActivityKind.MEAL,
                title="牛首山佛顶寺素斋馆 / 景区简餐",
                place_id="tm_place_niushoushan",
                start_at=datetime(2026, 10, 4, 14, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 15, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=12000, currency="CNY"),
                priority=60,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="品尝清雅佛门素面与精致素食小点",
                notes=["位于佛顶寺旁，清幽雅致"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0404-0000-000000000004"),
                kind=ActivityKind.FREE_TIME,
                title="先锋书店(五台山总店) & 新街口商圈漫步",
                place_id="tm_place_xinjiekou",
                start_at=datetime(2026, 10, 4, 16, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 18, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=70,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="防空洞改造的世界最美书店之一，南京文化精神地标",
                notes=["G70转地铁1号线返回新街口，步行至广州路五台山先锋书店"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0405-0000-000000000005"),
                kind=ActivityKind.MEAL,
                title="南京大牌档 / 新街口德基精品餐饮",
                place_id="tm_place_nanjing_dapaidang",
                start_at=datetime(2026, 10, 4, 19, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 20, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=20000, currency="CNY"),
                priority=65,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="新街口核心商圈丰富晚宴选择",
                notes=["新街口商圈核心餐饮区"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0406-0000-000000000006"),
                kind=ActivityKind.REST,
                title="步行返回金陵饭店(新街口店) 休息",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 4, 20, 45, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 4, 21, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=90,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="步行返回酒店大堂安歇",
                notes=["步行约300米返回酒店"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
        ]
        days.append(
            DayPlan(
                date=d4_date,
                day_number=4,
                theme="春牛首禅意奇观与书香金陵",
                weather=_build_weather(d4_date, WeatherCondition.CLEAR, 18.0, 26.0, 0.0),
                activities=d4_acts,
                route_legs=[r4_leg1],
                statistics=DayStatistics(activity_count=6, walking_meters=3900, transfer_minutes=75, planned_minutes=450, estimated_cost=Money(amount=62200, currency="CNY")),
                warnings=[],
            )
        )

        # ---------- Day 5: 颐和路民国街区漫步、退房与高铁返杭 ----------
        d5_date = date(2026, 10, 5)
        r5_leg1_id = UUID(f"77777777-500{version}-0001-0000-000000000001")
        r5_leg1 = RouteLeg(
            id=r5_leg1_id,
            origin_place_id="tm_place_jinling_hotel",
            destination_place_id="tm_place_nanjing_south_station",
            mode=TransportMode.PUBLIC_TRANSIT,
            departure_time=datetime(2026, 10, 5, 14, 0, 0, tzinfo=CST),
            arrival_time=datetime(2026, 10, 5, 15, 0, 0, tzinfo=CST),
            duration_minutes=60,
            distance_meters=8500,
            walking_meters=400,
            cost=Money(amount=400, currency="CNY"),
            instructions_summary="地铁1号线 (新街口站→南京南站，约25分钟，南落客平台直达候车大厅)",
            source=_build_source("AmapRouteMatrix"),
        )
        d5_acts = [
            Activity(
                id=UUID(f"77777777-000{version}-0501-0000-000000000001"),
                kind=ActivityKind.CHECK_OUT,
                title="金陵饭店(新街口店) 办理退房与行李寄存",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 5, 9, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 5, 9, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=95,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="办理退房并将大件行李寄存礼宾部，轻装开启半日漫游",
                notes=["礼宾部出示房卡办理行李免费寄存"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0502-0000-000000000002"),
                kind=ActivityKind.VISIT,
                title="颐和路历史文化街区 (一条颐和路，半部民国史)",
                place_id="tm_place_laomendong",
                start_at=datetime(2026, 10, 5, 9, 45, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 5, 12, 0, 0, tzinfo=CST),
                estimated_cost=Money(amount=0, currency="CNY"),
                priority=80,
                locked=False,
                indoor_outdoor=IndoorOutdoor.OUTDOOR,
                reason="绿树掩映中的金陵民国公馆建筑群，宁静安详",
                notes=["地铁1号线 (新街口站→鼓楼站换乘4号线→云南路站，约12分钟，5号口出步行450米)"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0503-0000-000000000003"),
                kind=ActivityKind.MEAL,
                title="颐和公馆·西餐厅 / 周边精致轻食",
                place_id="tm_place_honggongguan",
                start_at=datetime(2026, 10, 5, 12, 15, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 5, 13, 30, 0, tzinfo=CST),
                estimated_cost=Money(amount=22000, currency="CNY"),
                priority=65,
                locked=False,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="民国风貌保护区内享用优雅午餐",
                notes=["位于颐和路第十一片区内"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0504-0000-000000000004"),
                kind=ActivityKind.TRANSFER,
                title="返回金陵饭店提取行李并乘地铁1号线直达南京南站",
                place_id="tm_place_jinling_hotel",
                start_at=datetime(2026, 10, 5, 14, 0, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 5, 15, 0, 0, tzinfo=CST),
                route_leg_id=r5_leg1_id,
                estimated_cost=Money(amount=800, currency="CNY"),
                priority=100,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="前往南京南站高铁枢纽",
                notes=["地铁4号线转1号线取行李后，乘坐地铁1号线直达南京南站，约25分钟"],
                source_type=ActivitySourceType.PLANNER,
            ),
            Activity(
                id=UUID(f"77777777-000{version}-0505-0000-000000000005"),
                kind=ActivityKind.FREE_TIME,
                title="南京南站 候车并乘高铁返程杭州",
                place_id="tm_place_nanjing_south_station",
                start_at=datetime(2026, 10, 5, 15, 30, 0, tzinfo=CST),
                end_at=datetime(2026, 10, 5, 16, 45, 0, tzinfo=CST),
                estimated_cost=Money(amount=23500, currency="CNY"),
                priority=100,
                locked=True,
                indoor_outdoor=IndoorOutdoor.INDOOR,
                reason="南京南站候车乘车，圆满结束金陵 5 日游",
                notes=["南京南站二楼候车大厅检票口乘车，高铁约1小时15分直达杭州东站"],
                source_type=ActivitySourceType.FIXED_RULE,
            ),
        ]
        days.append(
            DayPlan(
                date=d5_date,
                day_number=5,
                theme="颐和梧桐剪影与高铁返程",
                weather=_build_weather(d5_date, WeatherCondition.CLEAR, 17.0, 25.0, 0.0),
                activities=d5_acts,
                route_legs=[r5_leg1],
                statistics=DayStatistics(activity_count=5, walking_meters=3200, transfer_minutes=60, planned_minutes=330, estimated_cost=Money(amount=46300, currency="CNY")),
                warnings=[],
            )
        )

        return days

    # 汇总预算
    def build_itinerary(version: int, days: list[DayPlan]) -> Itinerary:
        total_cents = sum(d.statistics.estimated_cost.amount for d in days)
        budget_summary = _build_budget_summary(
            800000,
            [
                (BudgetCategory.ACCOMMODATION, "金陵饭店(新街口店) 4 晚双人住宿", 320000),
                (BudgetCategory.FOOD, "南京大牌档、红公馆、江南灶、小厨娘等特色餐饮", 120000),
                (BudgetCategory.INTERCITY_TRANSPORT, "杭州东-南京南 往返高铁二等座 2 人", 47007),
                (BudgetCategory.LOCAL_TRANSPORT, "南京地铁 1/2/3/4 号线市内刷卡乘车", 6000),
                (BudgetCategory.ADMISSION, "牛首山门票、总统府门票、秦淮画舫等", 65000),
            ],
        )

        return Itinerary(
            trip_id=trip_id,
            title="南京 5 日深度文化与美食之旅",
            destination="南京",
            timezone="Asia/Shanghai",
            date_range=request.date_range,
            days=days,
            budget=budget_summary,
            general_notes=[
                "身份证件原件及复印件（南京博物院、总统府、大屠杀遇难同胞纪念馆严格实名刷身份证入园）",
                "重点文博场馆提前预约（南京博物院提前7天晚18点放票，建议提前预约）",
                "金陵通 / 微信江苏交通一卡通乘车二维码已开通",
                "备好轻便舒适步行鞋与晴雨两用伞",
            ],
            generated_at=now,
        )

    v1_days = build_nanjing_days(1)
    v2_days = build_nanjing_days(2)
    v3_days = build_nanjing_days(3)

    v1_itin = build_itinerary(1, v1_days)
    v2_itin = build_itinerary(2, v2_days)
    v3_itin = build_itinerary(3, v3_days)

    passed_report = ConstraintReport(
        passed=True,
        violations=[],
        checked_rule_codes=[c.value for c in ConstraintCode],
        checked_at=now,
        engine_version="1.0.0",
    )

    plan_v1 = PlanVersionRecord(
        id=plan_id_v1,
        trip_id=trip_id,
        version=1,
        parent_version=None,
        status=PlanStatus.SUPERSEDED,
        trigger=PlanTrigger.INITIAL,
        itinerary=v1_itin,
        constraint_report=passed_report,
        change_summary="初始全量行程规划（以金陵饭店为枢纽）",
        planning_run_id=run_id_v1,
        created_at=now,
        accepted_at=None,
    )

    plan_v2 = PlanVersionRecord(
        id=plan_id_v2,
        trip_id=trip_id,
        version=2,
        parent_version=1,
        status=PlanStatus.SUPERSEDED,
        trigger=PlanTrigger.USER_FEEDBACK,
        itinerary=v2_itin,
        constraint_report=passed_report,
        change_summary="Day 2 晚出发并保留玄武湖日落",
        planning_run_id=run_id_v2,
        created_at=now,
        accepted_at=None,
    )

    plan_v3 = PlanVersionRecord(
        id=plan_id_v3,
        trip_id=trip_id,
        version=3,
        parent_version=2,
        status=PlanStatus.ACCEPTED,
        trigger=PlanTrigger.USER_FEEDBACK,
        itinerary=v3_itin,
        constraint_report=passed_report,
        change_summary="减少每日步行距离并优化地铁观光车接驳（已确认）",
        planning_run_id=run_id_v3,
        created_at=now,
        accepted_at=now,
    )

    # 5. 事件流水记录
    events = [
        PlanningEventRecord(
            id="77777777-e001-0000-0000-000000000001",
            run_id=run_id_v1,
            sequence=1,
            type=PlanningEventType.RUN_STARTED,
            step="research",
            message="初次规划流水启动：基于南京真实 POI 与交通拓扑生成日程",
            payload={"destination": "南京", "hotel": "金陵饭店(新街口店)"},
            created_at=now,
        ),
        PlanningEventRecord(
            id="77777777-e001-0000-0000-000000000002",
            run_id=run_id_v2,
            sequence=1,
            type=PlanningEventType.STEP_COMPLETED,
            step="planning",
            message="解析用户反馈：Day 2 晚出发偏好与玄武湖日落",
            payload={"operations": fb_1.operations},
            created_at=now,
        ),
        PlanningEventRecord(
            id="77777777-e001-0000-0000-000000000003",
            run_id=run_id_v3,
            sequence=1,
            type=PlanningEventType.RUN_COMPLETED,
            step="completed",
            message="全量硬性约束校验 100% 通过，已生成最终版本 v3",
            payload={"version": 3, "status": "accepted"},
            created_at=now,
        ),
    ]

    return trip, [plan_v1, plan_v2, plan_v3], [run_v1, run_v2, run_v3], events, [fb_1, fb_2]


# ==========================================
# 方案 2：北京 4 日游（阶段 1 初次规划草案阶段）
# ==========================================
def create_beijing_draft_trip_and_version(now: datetime) -> tuple[TripRecord, list[PlanVersionRecord], list[PlanningRunRecord], list[PlanningEventRecord], list[FeedbackRecord]]:
    trip_id = UUID("99999999-9999-9999-9999-999999999999")
    run_id_v1 = UUID("99999999-0001-0000-0000-000000000001")
    plan_id_v1 = UUID("99999999-0001-0001-0001-000100010001")

    # 1. 旅行请求
    request = TripRequest(
        origin="上海",
        destination="北京",
        destination_timezone="Asia/Shanghai",
        date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 4)),
        travelers=2,
        preferences=TripPreferences(
            interests=[
                WeightedPreference(value="文化古迹", weight=0.95),
                WeightedPreference(value="地道美食", weight=0.85),
                WeightedPreference(value="胡同漫步", weight=0.75),
            ],
            avoid=[],
            dietary=[],
            transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
            accommodation_notes="入住北京王府井希尔顿酒店，近地铁8号线金鱼胡同站与1号线王府井站",
            pace=Pace.BALANCED,
            must_visit_place_names=["故宫博物院", "天坛公园", "颐和园"],
        ),
        constraints=TripConstraints(
            total_budget=Money(amount=1000000, currency="CNY"),
            budget_is_hard_limit=True,
            daily_start_time="08:30",
            daily_end_time="21:00",
            max_walking_meters_per_day=12000,
            max_activities_per_day=6,
            minimum_transfer_buffer_minutes=10,
            rest_minutes_per_day=60,
            required_place_names=["故宫博物院", "天坛公园", "颐和园"],
            excluded_place_names=[],
            accessible_only=False,
        ),
        locale="zh-CN",
        display_currency="CNY",
        notes="京沪高铁抵达北京南站，入住王府井希尔顿，深度游览故宫与颐和园，品尝地道烤鸭。",
    )

    trip = TripRecord(
        id=trip_id,
        status=TripStatus.NEEDS_REVIEW,
        revision=1,
        request=request,
        current_plan_version=1,
        active_planning_run_id=None,
        created_at=now,
        updated_at=now,
    )

    # 2. 规划任务记录 v1
    run_v1 = PlanningRunRecord(
        id=run_id_v1,
        trip_id=trip_id,
        trigger=PlanningRunTrigger.INITIAL,
        status=PlanningRunStatus.COMPLETED,
        progress_percent=100,
        current_step="completed",
        base_plan_version=None,
        result_plan_version=1,
        feedback_id=None,
        repair_attempts=0,
        max_repair_attempts=3,
        error=None,
        created_at=now,
        started_at=now,
        finished_at=now,
    )

    # 3. 构建北京真实 4 日日程
    d1_date = date(2026, 10, 1)
    bj_r1_leg1_id = UUID("99999999-1001-0001-0000-000000000001")
    bj_r1_leg1 = RouteLeg(
        id=bj_r1_leg1_id,
        origin_place_id="tm_place_beijing_south_station",
        destination_place_id="tm_place_wangfujing_hilton",
        mode=TransportMode.PUBLIC_TRANSIT,
        departure_time=datetime(2026, 10, 1, 9, 30, 0, tzinfo=CST),
        arrival_time=datetime(2026, 10, 1, 10, 15, 0, tzinfo=CST),
        duration_minutes=45,
        distance_meters=11000,
        walking_meters=450,
        cost=Money(amount=500, currency="CNY"),
        instructions_summary="地铁4号线转1号线 (北京南站→西单站换乘1号线→王府井站，约28分钟，C2口出步行400米)",
        source=_build_source("AmapRouteMatrix"),
    )
    d1_acts = [
        Activity(
            id=UUID("99999999-0001-0101-0000-000000000001"),
            kind=ActivityKind.TRANSFER,
            title="京沪高铁抵达北京南站，换乘地铁4号线转1号线",
            place_id="tm_place_beijing_south_station",
            start_at=datetime(2026, 10, 1, 9, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 10, 15, 0, tzinfo=CST),
            route_leg_id=bj_r1_leg1_id,
            estimated_cost=Money(amount=1000, currency="CNY"),
            priority=100,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="京沪高铁抵达北京南站，前往王府井酒店",
            notes=["地铁4号线转1号线 (北京南站→西单站换乘1号线→王府井站，约28分钟，C2口出)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0102-0000-000000000002"),
            kind=ActivityKind.CHECK_IN,
            title="北京王府井希尔顿酒店 办理入住与行李寄存",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 1, 10, 15, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 11, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="王府井核心商圈五星级大本营，邻近金鱼胡同站",
            notes=["王府井站步行约400米到达金鱼胡同希尔顿酒店前台办理入住与行李寄存"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
        Activity(
            id=UUID("99999999-0001-0103-0000-000000000003"),
            kind=ActivityKind.MEAL,
            title="局气(王府井店)",
            place_id="tm_place_juqi",
            start_at=datetime(2026, 10, 1, 11, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 13, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=22000, currency="CNY"),
            priority=70,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝地道老北京家常菜、蜂窝煤炒饭与乾隆白菜",
            notes=["步行至王府井百货大楼6层"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0104-0000-000000000004"),
            kind=ActivityKind.VISIT,
            title="天坛公园 (祈年殿、皇穹宇与回音壁)",
            place_id="tm_place_tiantan",
            start_at=datetime(2026, 10, 1, 13, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 17, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=6800, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="明清两代皇帝祭天胜地，中国古代祭祀建筑之巅峰",
            notes=["地铁8号线转5号线 (金鱼胡同站乘8号线至前门转2号线/5号线至天坛东门站，约20分钟，A口出)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0105-0000-000000000005"),
            kind=ActivityKind.MEAL,
            title="全聚德(前门店)",
            place_id="tm_place_quanjude",
            start_at=datetime(2026, 10, 1, 17, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 19, 30, 0, tzinfo=CST),
            estimated_cost=Money(amount=36000, currency="CNY"),
            priority=75,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="前门步行街百余年老店，正宗传统挂炉烤鸭盛宴",
            notes=["地铁5号线至崇文门转2号线至前门站，步行至前门大街30号"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0106-0000-000000000006"),
            kind=ActivityKind.REST,
            title="返回北京王府井希尔顿酒店 休息",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 1, 20, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 1, 20, 45, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="结束首日行程返回酒店休息",
            notes=["地铁8号线 (前门站→金鱼胡同站，约10分钟，B口出直通酒店大堂)"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
    ]

    d2_date = date(2026, 10, 2)
    bj_r2_leg1_id = UUID("99999999-2001-0001-0000-000000000001")
    bj_r2_leg1 = RouteLeg(
        id=bj_r2_leg1_id,
        origin_place_id="tm_place_wangfujing_hilton",
        destination_place_id="tm_place_forbidden_city",
        mode=TransportMode.PUBLIC_TRANSIT,
        departure_time=datetime(2026, 10, 2, 8, 30, 0, tzinfo=CST),
        arrival_time=datetime(2026, 10, 2, 9, 0, 0, tzinfo=CST),
        duration_minutes=30,
        distance_meters=2800,
        walking_meters=400,
        cost=Money(amount=300, currency="CNY"),
        instructions_summary="地铁1号线 (王府井站→天安门东站，约4分钟，B口出步行至午门检票口)",
        source=_build_source("AmapRouteMatrix"),
    )
    d2_acts = [
        Activity(
            id=UUID("99999999-0001-0201-0000-000000000001"),
            kind=ActivityKind.TRANSFER,
            title="北京王府井希尔顿酒店 出发前往故宫午门",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 2, 8, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 9, 0, 0, tzinfo=CST),
            route_leg_id=bj_r2_leg1_id,
            estimated_cost=Money(amount=600, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="乘地铁前往天安门东站",
            notes=["地铁1号线 (王府井站→天安门东站，约4分钟，B口出步行至午门检票口)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0202-0000-000000000002"),
            kind=ActivityKind.VISIT,
            title="故宫博物院 (午门进，中轴三大殿与珍宝馆深度游)",
            place_id="tm_place_forbidden_city",
            start_at=datetime(2026, 10, 2, 9, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 13, 30, 0, tzinfo=CST),
            estimated_cost=Money(amount=12000, currency="CNY"),
            priority=100,
            locked=True,
            indoor_outdoor=IndoorOutdoor.MIXED,
            reason="明清两代皇家宫殿，世界五大宫之首",
            notes=["提前7天实名预约，携带二代身份证原件由午门刷证入宫，神武门出宫"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0203-0000-000000000003"),
            kind=ActivityKind.MEAL,
            title="四季民福烤鸭店(故宫店)",
            place_id="tm_place_sijiminfu",
            start_at=datetime(2026, 10, 2, 13, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 15, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=32000, currency="CNY"),
            priority=85,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="神武门出宫后漫步至东华门外，边赏筒子河角楼边品尝酥脆烤鸭",
            notes=["神武门出宫步行约600米即达南池子大街东华门外"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0204-0000-000000000004"),
            kind=ActivityKind.VISIT,
            title="景山公园 (万春亭俯瞰紫禁城全景)",
            place_id="tm_place_jingshan",
            start_at=datetime(2026, 10, 2, 15, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 17, 30, 0, tzinfo=CST),
            estimated_cost=Money(amount=400, currency="CNY"),
            priority=80,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="北京中轴线最高点，夕阳西下尽览金碧辉煌紫禁城全貌",
            notes=["故宫神武门正对面直接进入景山公园南门，登顶万春亭"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0205-0000-000000000005"),
            kind=ActivityKind.FREE_TIME,
            title="什刹海 & 烟袋斜街胡同漫步",
            place_id="tm_place_shichahai",
            start_at=datetime(2026, 10, 2, 18, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 20, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=70,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="银锭桥畔、后海湖畔与老北京胡同夜景风情",
            notes=["从景山西门步行至什刹海前海周边"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0206-0000-000000000006"),
            kind=ActivityKind.REST,
            title="返回北京王府井希尔顿酒店 休息",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 2, 20, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 2, 21, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="乘地铁返回酒店休息",
            notes=["地铁8号线 (什刹海站→金鱼胡同站，约8分钟，B口出直通酒店)"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
    ]

    d3_date = date(2026, 10, 3)
    bj_r3_leg1_id = UUID("99999999-3001-0001-0000-000000000001")
    bj_r3_leg1 = RouteLeg(
        id=bj_r3_leg1_id,
        origin_place_id="tm_place_wangfujing_hilton",
        destination_place_id="tm_place_summer_palace",
        mode=TransportMode.PUBLIC_TRANSIT,
        departure_time=datetime(2026, 10, 3, 9, 0, 0, tzinfo=CST),
        arrival_time=datetime(2026, 10, 3, 9, 45, 0, tzinfo=CST),
        duration_minutes=45,
        distance_meters=18000,
        walking_meters=450,
        cost=Money(amount=600, currency="CNY"),
        instructions_summary="地铁8号线转4号线 (金鱼胡同站→平安里站换乘4号线→北宫门站，约40分钟，D口出)",
        source=_build_source("AmapRouteMatrix"),
    )
    d3_acts = [
        Activity(
            id=UUID("99999999-0001-0301-0000-000000000001"),
            kind=ActivityKind.TRANSFER,
            title="北京王府井希尔顿酒店 出发前往颐和园",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 3, 9, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 9, 45, 0, tzinfo=CST),
            route_leg_id=bj_r3_leg1_id,
            estimated_cost=Money(amount=1000, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="地铁8号线转4号线前往海淀颐和园",
            notes=["地铁8号线转4号线 (金鱼胡同站→平安里站换乘4号线→北宫门站，约40分钟，D口出)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0302-0000-000000000002"),
            kind=ActivityKind.VISIT,
            title="颐和园 (长廊、佛香阁与昆明湖画舫)",
            place_id="tm_place_summer_palace",
            start_at=datetime(2026, 10, 3, 9, 45, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 14, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=12000, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="保存最完整的皇家行宫御苑，万寿山佛香阁与十七孔桥",
            notes=["北宫门入园，漫步苏州街、长廊并乘昆明湖画舫渡船"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0303-0000-000000000003"),
            kind=ActivityKind.MEAL,
            title="白魁老号饭庄 / 颐和园周边老字号午餐",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 3, 14, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 16, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=18000, currency="CNY"),
            priority=65,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝经典北京清真特色菜与小吃",
            notes=["颐和园北宫门周边餐饮"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0304-0000-000000000004"),
            kind=ActivityKind.VISIT,
            title="中国国家博物馆 (古代中国基本陈列)",
            place_id="tm_place_national_museum",
            start_at=datetime(2026, 10, 3, 16, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 19, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="中华文明国家最高历史文化殿堂，后母戊鼎与四羊方尊",
            notes=["地铁4号线转1号线 (北宫门站→西单站换乘1号线→天安门东站，约35分钟)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0305-0000-000000000005"),
            kind=ActivityKind.MEAL,
            title="王府井东方新天地特色餐饮",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 3, 19, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 20, 45, 0, tzinfo=CST),
            estimated_cost=Money(amount=24000, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="王府井商圈核心餐饮与休闲",
            notes=["王府井站直通东方新天地"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0306-0000-000000000006"),
            kind=ActivityKind.REST,
            title="步行返回北京王府井希尔顿酒店 休息",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 3, 21, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 3, 21, 15, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="王府井大街漫步约5分钟返回酒店大堂",
            notes=["步行约350米返回酒店"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
    ]

    d4_date = date(2026, 10, 4)
    bj_r4_leg1_id = UUID("99999999-4001-0001-0000-000000000001")
    bj_r4_leg1 = RouteLeg(
        id=bj_r4_leg1_id,
        origin_place_id="tm_place_wangfujing_hilton",
        destination_place_id="tm_place_beijing_south_station",
        mode=TransportMode.PUBLIC_TRANSIT,
        departure_time=datetime(2026, 10, 4, 14, 0, 0, tzinfo=CST),
        arrival_time=datetime(2026, 10, 4, 15, 0, 0, tzinfo=CST),
        duration_minutes=60,
        distance_meters=11000,
        walking_meters=450,
        cost=Money(amount=500, currency="CNY"),
        instructions_summary="地铁8号线转4号线 (金鱼胡同站→宣武门站换乘4号线→北京南站，约35分钟)",
        source=_build_source("AmapRouteMatrix"),
    )
    d4_acts = [
        Activity(
            id=UUID("99999999-0001-0401-0000-000000000001"),
            kind=ActivityKind.CHECK_OUT,
            title="北京王府井希尔顿酒店 办理退房与行李寄存",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 4, 9, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 4, 9, 30, 0, tzinfo=CST),
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="前台办理退房并寄存大件行李",
            notes=["前台礼宾部免费寄存"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
        Activity(
            id=UUID("99999999-0001-0402-0000-000000000002"),
            kind=ActivityKind.VISIT,
            title="雍和宫 & 国子监街",
            place_id="tm_place_yonghegong",
            start_at=datetime(2026, 10, 4, 9, 45, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 4, 12, 0, 0, tzinfo=CST),
            estimated_cost=Money(amount=5000, currency="CNY"),
            priority=85,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="北京最大藏传佛教寺院与皇家最高学府国子监",
            notes=["地铁8号线转2号线 (金鱼胡同站转2号线至雍和宫站，约18分钟，F口出)"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0403-0000-000000000003"),
            kind=ActivityKind.MEAL,
            title="金鼎轩(地坛总店)",
            place_id="tm_place_jindingxuan",
            start_at=datetime(2026, 10, 4, 12, 15, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 4, 13, 30, 0, tzinfo=CST),
            estimated_cost=Money(amount=20000, currency="CNY"),
            priority=70,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="雍和宫北侧和平里西街，品尝正宗粤港点心与川鲁佳肴",
            notes=["雍和宫向北步行约400米至地坛南门旁"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0404-0000-000000000004"),
            kind=ActivityKind.TRANSFER,
            title="返回酒店取行李，乘坐地铁前往北京南站",
            place_id="tm_place_wangfujing_hilton",
            start_at=datetime(2026, 10, 4, 14, 0, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 4, 15, 0, 0, tzinfo=CST),
            route_leg_id=bj_r4_leg1_id,
            estimated_cost=Money(amount=1000, currency="CNY"),
            priority=100,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="前往北京南站高铁枢纽",
            notes=["地铁8号线取行李后转4号线直达北京南站，约35分钟"],
            source_type=ActivitySourceType.PLANNER,
        ),
        Activity(
            id=UUID("99999999-0001-0405-0000-000000000005"),
            kind=ActivityKind.FREE_TIME,
            title="北京南站 候车并乘京沪高铁返程上海",
            place_id="tm_place_beijing_south_station",
            start_at=datetime(2026, 10, 4, 15, 30, 0, tzinfo=CST),
            end_at=datetime(2026, 10, 4, 16, 45, 0, tzinfo=CST),
            estimated_cost=Money(amount=120000, currency="CNY"),
            priority=100,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="乘京沪高铁复兴号返程上海虹桥站",
            notes=["北京南站高架候车大厅检票乘车，约4.5小时直达上海虹桥"],
            source_type=ActivitySourceType.FIXED_RULE,
        ),
    ]

    bj_days = [
        DayPlan(
            date=d1_date,
            day_number=1,
            theme="抵京安顿、天坛祈年与前门烤鸭",
            weather=_build_weather(d1_date, WeatherCondition.CLEAR, 12.0, 22.0, 0.0),
            activities=d1_acts,
            route_legs=[bj_r1_leg1],
            statistics=DayStatistics(activity_count=6, walking_meters=5200, transfer_minutes=65, planned_minutes=420, estimated_cost=Money(amount=65800, currency="CNY")),
            warnings=[],
        ),
        DayPlan(
            date=d2_date,
            day_number=2,
            theme="紫禁皇家风范、景山全景与什刹海胡同",
            weather=_build_weather(d2_date, WeatherCondition.CLEAR, 11.0, 21.0, 0.0),
            activities=d2_acts,
            route_legs=[bj_r2_leg1],
            statistics=DayStatistics(activity_count=6, walking_meters=6800, transfer_minutes=45, planned_minutes=460, estimated_cost=Money(amount=45000, currency="CNY")),
            warnings=[],
        ),
        DayPlan(
            date=d3_date,
            day_number=3,
            theme="颐和行宫画卷与国博中华瑰宝",
            weather=_build_weather(d3_date, WeatherCondition.CLOUDY, 13.0, 20.0, 0.05),
            activities=d3_acts,
            route_legs=[bj_r3_leg1],
            statistics=DayStatistics(activity_count=6, walking_meters=5900, transfer_minutes=80, planned_minutes=440, estimated_cost=Money(amount=55000, currency="CNY")),
            warnings=[],
        ),
        DayPlan(
            date=d4_date,
            day_number=4,
            theme="雍和禅韵、地道点心与高铁返程",
            weather=_build_weather(d4_date, WeatherCondition.CLEAR, 10.0, 19.0, 0.0),
            activities=d4_acts,
            route_legs=[bj_r4_leg1],
            statistics=DayStatistics(activity_count=5, walking_meters=3600, transfer_minutes=55, planned_minutes=330, estimated_cost=Money(amount=146000, currency="CNY")),
            warnings=[],
        ),
    ]

    bj_budget = _build_budget_summary(
        1000000,
        [
            (BudgetCategory.ACCOMMODATION, "北京王府井希尔顿酒店 3 晚住宿", 360000),
            (BudgetCategory.FOOD, "四季民福、全聚德、局气、金鼎轩等京味美食", 150000),
            (BudgetCategory.INTERCITY_TRANSPORT, "京沪高铁复兴号二等座 2 人往返", 120000),
            (BudgetCategory.LOCAL_TRANSPORT, "北京地铁 1/2/4/5/8 号线乘车", 7000),
            (BudgetCategory.ADMISSION, "故宫、天坛、颐和园、雍和宫门票", 31200),
        ],
    )

    bj_itin = Itinerary(
        trip_id=trip_id,
        title="北京 4 日中轴皇家古迹与胡同风情之旅",
        destination="北京",
        timezone="Asia/Shanghai",
        date_range=request.date_range,
        days=bj_days,
        budget=bj_budget,
        general_notes=[
            "携带二代身份证原件（故宫、国博、天坛、颐和园全网实名预约并刷身份证入园）",
            "故宫博物院提前7天晚20:00放票，国博提前7天放票，务必提前锁定预约",
            "已开通‘亿通行’或微信乘车码乘坐北京地铁",
            "北京秋季早晚温差较大，备好保暖外套与平底步行鞋",
        ],
        generated_at=now,
    )

    passed_report = ConstraintReport(
        passed=True,
        violations=[],
        checked_rule_codes=[c.value for c in ConstraintCode],
        checked_at=now,
        engine_version="1.0.0",
    )

    plan_v1 = PlanVersionRecord(
        id=plan_id_v1,
        trip_id=trip_id,
        version=1,
        parent_version=None,
        status=PlanStatus.DRAFT,
        trigger=PlanTrigger.INITIAL,
        itinerary=bj_itin,
        constraint_report=passed_report,
        change_summary="初次全量行程规划草案（以王府井希尔顿为枢纽，待审阅）",
        planning_run_id=run_id_v1,
        created_at=now,
        accepted_at=None,
    )

    events = [
        PlanningEventRecord(
            id="99999999-e001-0000-0000-000000000001",
            run_id=run_id_v1,
            sequence=1,
            type=PlanningEventType.RUN_STARTED,
            step="research",
            message="初次规划流水启动：基于北京真实 POI 与地铁网络构建草案",
            payload={"destination": "北京", "hotel": "北京王府井希尔顿酒店"},
            created_at=now,
        ),
        PlanningEventRecord(
            id="99999999-e001-0000-0000-000000000002",
            run_id=run_id_v1,
            sequence=2,
            type=PlanningEventType.PLAN_CREATED,
            step="completed",
            message="阶段 1 草案规划完成，硬约束全部通过，等待用户审阅",
            payload={"version": 1, "status": "draft"},
            created_at=now,
        ),
    ]

    return trip, [plan_v1], [run_v1], events, []


def seed_database(db_url: str) -> None:
    """执行数据库种子填充。"""
    print(f"[Seed] 正在连接数据库: {db_url}")

    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    repo = SqlAlchemyTravelRepository(session_factory)

    now = datetime(2026, 8, 19, 15, 30, 0, tzinfo=CST)

    # 1. 构建两条真实方案
    nanjing_trip, nanjing_plans, nanjing_runs, nanjing_events, nanjing_feedbacks = create_nanjing_trip_and_versions(now)
    beijing_trip, beijing_plans, beijing_runs, beijing_events, beijing_feedbacks = create_beijing_draft_trip_and_version(now)

    trips_to_seed = [
        (nanjing_trip, nanjing_plans, nanjing_runs, nanjing_events, nanjing_feedbacks),
        (beijing_trip, beijing_plans, beijing_runs, beijing_events, beijing_feedbacks),
    ]

    # 2. 幂等清理并写入
    with session_factory() as session:
        for trip, plans, runs, events, feedbacks in trips_to_seed:
            # 清理旧同 ID 数据
            existing = repo.get_trip(trip.id)
            if existing:
                print(f"[Seed] 清理已存在旅行: {trip.id} ({trip.request.destination})")
                from app.persistence.schema import FeedbackTable, PlanningEventTable, PlanningRunTable, PlanVersionTable, TripTable
                session.query(FeedbackTable).filter(FeedbackTable.trip_id == trip.id).delete()
                session.query(PlanningEventTable).filter(PlanningEventTable.run_id.in_([r.id for r in runs])).delete()
                session.query(PlanVersionTable).filter(PlanVersionTable.trip_id == trip.id).delete()
                session.query(PlanningRunTable).filter(PlanningRunTable.trip_id == trip.id).delete()
                session.query(TripTable).filter(TripTable.id == trip.id).delete()
                session.commit()

            # 写入 Trip
            repo.add_trip(trip)
            print(f"[Seed] 已写入旅行: {trip.id} ({trip.request.destination} {trip.status.value})")

            # 写入 Planning Runs
            for run in runs:
                repo.add_run(run)
            print(f"  └─ 已写入 {len(runs)} 条规划任务")

            # 写入 Plan Versions
            for plan in plans:
                repo.add_plan(plan)
            print(f"  └─ 已写入 {len(plans)} 个计划版本")

            # 写入 Events
            for event in events:
                repo.add_event(event)
            print(f"  └─ 已写入 {len(events)} 条事件流水")

            # 写入 Feedbacks
            for fb in feedbacks:
                repo.add_feedback(fb)
            if feedbacks:
                print(f"  └─ 已写入 {len(feedbacks)} 条用户反馈")

    print("[Seed] 数据库种子填充完成！共写入 2 组完整业务用例。")

    # 3. 自动生成纯 PostgreSQL SQL 脚本
    sql_path = backend_dir / "scripts" / "seed_demo_data.sql"
    export_pure_postgres_sql(trips_to_seed, sql_path)
    print(f"[Seed] 已成功导出 PostgreSQL 脚本: {sql_path}")


def export_pure_postgres_sql(trips_data: list, output_file: Path) -> None:
    """生成原生 PostgreSQL SQL 脚本，包含 ::uuid, ::jsonb, ::timestamptz 显式类型转换。"""
    lines: list[str] = [
        "-- TravelMind PostgreSQL 演示数据初始化脚本",
        "-- 生成时间: 2026-08-19",
        "-- 包含南京 5 日游 (v1/v2/v3 确认方案) 与北京 4 日游 (阶段 1 草案方案)",
        "",
        "BEGIN;",
        "",
        "-- 1. 清理已有演示数据",
        "DELETE FROM user_feedbacks WHERE trip_id IN ('77777777-7777-7777-7777-777777777777', '99999999-9999-9999-9999-999999999999', '88888888-8888-8888-8888-888888888888');",
        "DELETE FROM planning_events WHERE trip_id IN ('77777777-7777-7777-7777-777777777777', '99999999-9999-9999-9999-999999999999', '88888888-8888-8888-8888-888888888888');",
        "DELETE FROM plan_versions WHERE trip_id IN ('77777777-7777-7777-7777-777777777777', '99999999-9999-9999-9999-999999999999', '88888888-8888-8888-8888-888888888888');",
        "DELETE FROM planning_runs WHERE trip_id IN ('77777777-7777-7777-7777-777777777777', '99999999-9999-9999-9999-999999999999', '88888888-8888-8888-8888-888888888888');",
        "DELETE FROM trips WHERE id IN ('77777777-7777-7777-7777-777777777777', '99999999-9999-9999-9999-999999999999', '88888888-8888-8888-8888-888888888888');",
        "",
    ]

    for trip, plans, runs, events, feedbacks in trips_data:
        dest = trip.request.destination
        lines.append(f"-- ========================================================")
        lines.append(f"-- 旅行方案: {dest} ({trip.id})")
        lines.append(f"-- ========================================================")

        # Trips table
        req_json = json.dumps(trip.request.model_dump(mode="json"), ensure_ascii=False).replace("'", "''")
        active_run = f"'{trip.active_planning_run_id}'::uuid" if trip.active_planning_run_id else "NULL"
        cur_ver = f"{trip.current_plan_version}" if trip.current_plan_version is not None else "NULL"
        created_at_iso = trip.created_at.isoformat()
        updated_at_iso = trip.updated_at.isoformat()

        lines.append(
            f"INSERT INTO trips (id, status, revision, current_plan_version, active_planning_run_id, request_json, created_at, updated_at) "
            f"VALUES ('{trip.id}'::uuid, '{trip.status.value}', {trip.revision}, {cur_ver}, {active_run}, '{req_json}'::jsonb, '{created_at_iso}'::timestamptz, '{updated_at_iso}'::timestamptz);"
        )
        lines.append("")

        # Planning Runs
        for run in runs:
            err_val = f"'{run.error}'" if run.error else "NULL"
            fb_val = f"'{run.feedback_id}'::uuid" if run.feedback_id else "NULL"
            base_ver_val = f"{run.base_plan_version}" if run.base_plan_version is not None else "NULL"
            res_ver_val = f"{run.result_plan_version}" if run.result_plan_version is not None else "NULL"
            r_start = f"'{run.started_at.isoformat()}'::timestamptz" if run.started_at else "NULL"
            r_fin = f"'{run.finished_at.isoformat()}'::timestamptz" if run.finished_at else "NULL"

            lines.append(
                f"INSERT INTO planning_runs (id, trip_id, trigger, status, progress_percent, current_step, base_plan_version, result_plan_version, feedback_id, repair_attempts, max_repair_attempts, error, created_at, started_at, finished_at) "
                f"VALUES ('{run.id}'::uuid, '{run.trip_id}'::uuid, '{run.trigger.value}', '{run.status.value}', {run.progress_percent}, '{run.current_step}', {base_ver_val}, {res_ver_val}, {fb_val}, {run.repair_attempts}, {run.max_repair_attempts}, {err_val}, '{run.created_at.isoformat()}'::timestamptz, {r_start}, {r_fin});"
            )
        lines.append("")

        # Plan Versions
        for plan in plans:
            itin_json = json.dumps(plan.itinerary.model_dump(mode="json"), ensure_ascii=False).replace("'", "''")
            cr_json = json.dumps(plan.constraint_report.model_dump(mode="json"), ensure_ascii=False).replace("'", "''")
            p_ver_val = f"{plan.parent_version}" if plan.parent_version is not None else "NULL"
            summary_val = f"'{plan.change_summary}'" if plan.change_summary else "NULL"
            run_id_val = f"'{plan.planning_run_id}'::uuid" if plan.planning_run_id else "NULL"
            acc_val = f"'{plan.accepted_at.isoformat()}'::timestamptz" if plan.accepted_at else "NULL"

            lines.append(
                f"INSERT INTO plan_versions (id, trip_id, version, parent_version, status, trigger, itinerary_json, constraint_report_json, change_summary, planning_run_id, created_at, accepted_at) "
                f"VALUES ('{plan.id}'::uuid, '{plan.trip_id}'::uuid, {plan.version}, {p_ver_val}, '{plan.status.value}', '{plan.trigger.value}', '{itin_json}'::jsonb, '{cr_json}'::jsonb, {summary_val}, {run_id_val}, '{plan.created_at.isoformat()}'::timestamptz, {acc_val});"
            )
        lines.append("")

        # Planning Events
        for ev in events:
            ev_payload = json.dumps(ev.payload, ensure_ascii=False).replace("'", "''")
            step_val = f"'{ev.step}'" if ev.step else "NULL"

            lines.append(
                f"INSERT INTO planning_events (id, run_id, sequence, type, step, message, payload_json, created_at) "
                f"VALUES ('{ev.id}', '{ev.run_id}'::uuid, {ev.sequence}, '{ev.type.value}', {step_val}, '{ev.message}', '{ev_payload}'::jsonb, '{ev.created_at.isoformat()}'::timestamptz);"
            )
        lines.append("")

        # Feedbacks
        for fb in feedbacks:
            op_json = json.dumps(fb.operations, ensure_ascii=False).replace("'", "''")
            act_ids = json.dumps([str(i) for i in fb.affected_activity_ids])
            dates_json = json.dumps([d.isoformat() for d in fb.affected_dates])
            r_id_val = f"'{fb.planning_run_id}'::uuid" if fb.planning_run_id else "NULL"

            lines.append(
                f"INSERT INTO user_feedbacks (id, trip_id, base_plan_version, message, operations_json, affected_dates_json, affected_activity_ids_json, global_scope, requires_clarification, clarification_question, planning_run_id, created_at) "
                f"VALUES ('{fb.id}'::uuid, '{fb.trip_id}'::uuid, {fb.base_plan_version}, '{fb.message}', '{op_json}'::jsonb, '{dates_json}'::jsonb, '{act_ids}'::jsonb, {str(fb.global_scope).lower()}, {str(fb.requires_clarification).lower()}, NULL, {r_id_val}, '{fb.created_at.isoformat()}'::timestamptz);"
            )
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="TravelMind 演示数据种子生成工具")
    parser.add_argument("--db-url", type=str, default=None, help="目标数据库连接字符串")
    parser.add_argument("--test-db", action="store_true", help="是否写入测试数据库 (travelmind_test_db)")
    args = parser.parse_args()

    settings = get_settings()
    if args.db_url:
        target_url = args.db_url
    elif args.test_db:
        target_url = settings.TEST_DATABASE_URL
    else:
        target_url = settings.DATABASE_URL

    seed_database(target_url)


if __name__ == "__main__":
    main()
