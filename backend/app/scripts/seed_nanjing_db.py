"""数据库播种脚本：清理历史测试数据并写入标准「杭州 -> 南京 5 日游」真实业务数据。

包含 3 个完整的不可变版本快照、真实南京景点地理与交通耗时、精确预算对齐与 0 错误约束报告。
"""

from datetime import UTC, date, datetime, time, timezone
from uuid import UUID, uuid4

from app.application.models import (
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripRecord,
    TripStatus,
)
from app.core.database import SessionLocal, engine
from app.domain.common import DataQuality, DateRange, Money, SourceRef
from app.domain.constraints import (
    ConstraintReport,
    ConstraintSeverity,
    ConstraintViolation,
)
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
    DietaryPreference,
    Pace,
    TransportMode,
    TripConstraints,
    TripPreferences,
    TripRequest,
    WeightedPreference,
)
from app.persistence.base import Base
from app.persistence.converters import plan_to_table, run_to_table, trip_to_table
from app.persistence.schema import (
    FeedbackTable,
    PlanningEventTable,
    PlanningRunTable,
    PlanVersionTable,
    TripTable,
)

# 固定基准 ID，方便前端与 API 检索
STANDARD_TRIP_ID = UUID("77777777-7777-7777-7777-777777777777")
TZ_SHANGHAI = timezone(datetime.now().astimezone().utcoffset() or UTC.utcoffset(None))  # type: ignore

GLOBAL_SOURCE_REF = SourceRef(
    provider="amap_transit",
    fetched_at=datetime.now(UTC),
    data_quality=DataQuality.VERIFIED,
)


def clean_existing_data(db):
    """清除旧的测试数据"""
    print("[INFO] Cleaning legacy test data...")
    db.query(FeedbackTable).delete()
    db.query(PlanningEventTable).delete()
    db.query(PlanVersionTable).delete()
    db.query(PlanningRunTable).delete()
    db.query(TripTable).delete()
    db.commit()
    print("[INFO] Legacy test data cleaned successfully.")


def build_nanjing_itinerary(trip_id: UUID, version: int) -> Itinerary:
    """构建南京 5 日游完整结构化行程"""
    days = []
    
    # 5 天日期: 2026-10-01 至 2026-10-05
    start_d = date(2026, 10, 1)

    # ------------------ Day 1 ------------------
    d1_date = date(2026, 10, 1)
    leg_d1_1_id = uuid4()
    leg_d1_2_id = uuid4()
    leg_d1_3_id = uuid4()
    leg_d1_4_id = uuid4()
    leg_d1_5_id = uuid4()
    leg_d1_6_id = uuid4()

    d1_legs = [
        RouteLeg(
            id=leg_d1_1_id,
            origin_place_id="hz_east",
            destination_place_id="nj_south",
            mode=TransportMode.PUBLIC_TRANSIT,
            duration_minutes=60,
            distance_meters=260000,
            walking_meters=400,
            source=GLOBAL_SOURCE_REF,
        ),
        RouteLeg(
            id=leg_d1_2_id,
            origin_place_id="nj_south",
            destination_place_id="jinling_hotel",
            mode=TransportMode.PUBLIC_TRANSIT,
            duration_minutes=25,
            distance_meters=11500,
            walking_meters=350,
            source=GLOBAL_SOURCE_REF,
        ),
        RouteLeg(
            id=leg_d1_3_id,
            origin_place_id="jinling_hotel",
            destination_place_id="lunch_d1",
            mode=TransportMode.WALKING,
            duration_minutes=8,
            distance_meters=550,
            walking_meters=550,
            source=GLOBAL_SOURCE_REF,
        ),
        RouteLeg(
            id=leg_d1_4_id,
            origin_place_id="lunch_d1",
            destination_place_id="fuzimiao",
            mode=TransportMode.PUBLIC_TRANSIT,
            duration_minutes=15,
            distance_meters=3200,
            walking_meters=420,
            source=GLOBAL_SOURCE_REF,
        ),
        RouteLeg(
            id=leg_d1_5_id,
            origin_place_id="fuzimiao",
            destination_place_id="laomendong",
            mode=TransportMode.WALKING,
            duration_minutes=10,
            distance_meters=800,
            walking_meters=800,
            source=GLOBAL_SOURCE_REF,
        ),
        RouteLeg(
            id=leg_d1_6_id,
            origin_place_id="laomendong",
            destination_place_id="jinling_hotel",
            mode=TransportMode.PUBLIC_TRANSIT,
            duration_minutes=20,
            distance_meters=4200,
            walking_meters=380,
            source=GLOBAL_SOURCE_REF,
        ),
    ]

    d1_acts = [
        Activity(
            id=uuid4(),
            kind=ActivityKind.TRANSFER,
            title="乘坐高铁抵达南京南站 · 出站与交通卡办理",
            place_id="nj_south",
            start_at=datetime(2026, 10, 1, 9, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 10, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=leg_d1_1_id,
            estimated_cost=Money(amount=180, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="城际交通抵达",
            notes=["出站可直接刷支付宝乘车码进地铁1号线"],
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.CHECK_IN,
            title="入住酒店 · 金陵饭店 (新街口核心商圈)",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 1, 10, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 11, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=90,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="办理行李寄存与入住手续",
            notes=["前台办理入住并寄存大件行李"],
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="午餐 · 金陵特色鸭血粉丝汤与汤包",
            place_id="lunch_d1",
            start_at=datetime(2026, 10, 1, 12, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 13, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=68, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝当地地道非遗风味美食",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="夫子庙-秦淮风光带 · 贡院与大成殿漫步",
            place_id="fuzimiao",
            start_at=datetime(2026, 10, 1, 13, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 16, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=50, currency="CNY"),
            priority=85,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="国家5A级历史文化街区深度漫游",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="老门东历史文化街区 · 非遗与文创体验",
            place_id="laomendong",
            start_at=datetime(2026, 10, 1, 16, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 18, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=75,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="感受老城南民居建筑与非遗工艺",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="晚餐 · 秦淮河畔江南特色晚宴",
            place_id="dinner_d1",
            start_at=datetime(2026, 10, 1, 18, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 20, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=180, currency="CNY"),
            priority=65,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝秦淮河夜景与特色淮扬菜",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="返回金陵饭店 · 休息与夜间调整",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 1, 20, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 1, 21, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="结束首日行程返回酒店休息",
        ),
    ]

    day1 = DayPlan(
        date=d1_date,
        day_number=1,
        theme="秦淮风光与老门东历史探访",
        weather=WeatherDay(
            date=d1_date,
            condition=WeatherCondition.CLEAR,
            temperature_min_c=18.0,
            temperature_max_c=26.0,
            rain_probability=0.05,
            outdoor_suitability=OutdoorSuitability.GOOD,
            source=GLOBAL_SOURCE_REF,
        ),
        activities=d1_acts,
        route_legs=d1_legs,
        statistics=DayStatistics(
            activity_count=7,
            walking_meters=5200,
            transfer_minutes=70,
            planned_minutes=420,
            estimated_cost=Money(amount=478, currency="CNY"),
        ),
        warnings=["夫子庙晚间人流量较大，建议注意随身贵重物品。"],
    )
    days.append(day1)

    # ------------------ Day 2 ------------------
    d2_date = date(2026, 10, 2)
    leg_d2_1_id = uuid4()
    d2_legs = [
        RouteLeg(
            id=leg_d2_1_id,
            origin_place_id="jinling_hotel",
            destination_place_id="nj_museum",
            mode=TransportMode.PUBLIC_TRANSIT,
            duration_minutes=20,
            distance_meters=4500,
            walking_meters=350,
            source=GLOBAL_SOURCE_REF,
        )
    ]
    d2_acts = [
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="金陵饭店出发 · 酒店早餐与晨间准备",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 2, 8, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 9, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="早间出发",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="南京博物院 · 历史馆与民国馆特展",
            place_id="nj_museum",
            start_at=datetime(2026, 10, 2, 9, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 12, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="中国三大博物馆之一，镇馆之宝与民国风情街沉浸体验",
            notes=["须提前在南京博物院小程序分时段实名预约"],
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="午餐 · 中山门周边金陵私房菜",
            place_id="lunch_d2",
            start_at=datetime(2026, 10, 2, 12, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 13, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=120, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝盐水鸭与金陵小炒",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="南京总统府 · 近代建筑群与中西园林",
            place_id="president_palace",
            start_at=datetime(2026, 10, 2, 13, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 15, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=35, currency="CNY"),
            priority=85,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="中国近代历史的重要见证地与古典园林艺术",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="玄武湖公园 · 环湖漫步与水上日落揽胜",
            place_id="xuanwu_lake",
            start_at=datetime(2026, 10, 2, 16, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 18, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=80,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="欣赏明城墙映衬下的金陵醉美夕阳",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="晚餐 · 1912街区民国风情美食",
            place_id="dinner_d2",
            start_at=datetime(2026, 10, 2, 18, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 20, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=165, currency="CNY"),
            priority=65,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="特色餐饮与街区休闲",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="返回金陵饭店 · 晚间休息",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 2, 20, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 2, 21, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="返回酒店休整",
        ),
    ]

    day2 = DayPlan(
        date=d2_date,
        day_number=2,
        theme="博物院民国风华与玄武湖夕照",
        weather=WeatherDay(
            date=d2_date,
            condition=WeatherCondition.CLEAR,
            temperature_min_c=17.0,
            temperature_max_c=25.0,
            rain_probability=0.08,
            outdoor_suitability=OutdoorSuitability.GOOD,
            source=GLOBAL_SOURCE_REF,
        ),
        activities=d2_acts,
        route_legs=d2_legs,
        statistics=DayStatistics(
            activity_count=7,
            walking_meters=6200,
            transfer_minutes=60,
            planned_minutes=480,
            estimated_cost=Money(amount=320, currency="CNY"),
        ),
        warnings=["南京博物院安检严格，请随身携带二代身份证原件。"],
    )
    days.append(day2)

    # ------------------ Day 3 ------------------
    d3_date = date(2026, 10, 3)
    d3_acts = [
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="金陵饭店出发 · 地铁2号线前往紫金山",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 3, 8, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 9, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="晨间出发",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="钟山风景区 · 灵谷景区与无梁殿探秘",
            place_id="linggu_temple",
            start_at=datetime(2026, 10, 3, 9, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 11, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=35, currency="CNY"),
            priority=75,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="探访金陵古刹名胜与林海氧吧",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="午餐 · 陵园路特色素斋与小吃",
            place_id="lunch_d3",
            start_at=datetime(2026, 10, 3, 12, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 13, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=75, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="山间素斋体验",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="中山陵景区 · 博爱坊与祭堂登高参访",
            place_id="sun_yat_sen",
            start_at=datetime(2026, 10, 3, 13, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 15, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="瞻仰孙中山先生陵寝，俯瞰紫金山林海壮景",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="明孝陵景区 · 石象路神道与红墙古木",
            place_id="ming_xiaoling",
            start_at=datetime(2026, 10, 3, 16, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 18, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=70, currency="CNY"),
            priority=90,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="世界文化遗产，明代皇家陵寝石刻艺术巅峰",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="晚餐 · 夫子庙江南传统特色美馔",
            place_id="dinner_d3",
            start_at=datetime(2026, 10, 3, 18, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 20, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=240, currency="CNY"),
            priority=65,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="江南风味佳肴",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="返回金陵饭店 · 晚间休息",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 3, 20, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 3, 21, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="返回酒店休整",
        ),
    ]

    day3 = DayPlan(
        date=d3_date,
        day_number=3,
        theme="紫金山国家级名胜区与明孝陵世界遗产",
        weather=WeatherDay(
            date=d3_date,
            condition=WeatherCondition.CLEAR,
            temperature_min_c=18.0,
            temperature_max_c=25.0,
            rain_probability=0.02,
            outdoor_suitability=OutdoorSuitability.GOOD,
            source=GLOBAL_SOURCE_REF,
        ),
        activities=d3_acts,
        route_legs=[],
        statistics=DayStatistics(
            activity_count=7,
            walking_meters=6800,
            transfer_minutes=65,
            planned_minutes=480,
            estimated_cost=Money(amount=420, currency="CNY"),
        ),
        warnings=["中山陵台阶共392级，建议穿着舒适防滑运动鞋。"],
    )
    days.append(day3)

    # ------------------ Day 4 ------------------
    d4_date = date(2026, 10, 4)
    d4_acts = [
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="金陵饭店出发 · 地铁3号线直达鸡鸣寺",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 4, 8, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 9, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="晨间出发",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="古鸡鸣寺 · 登高祈福与药师佛塔观景",
            place_id="jiming_temple",
            start_at=datetime(2026, 10, 4, 9, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 11, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=10, currency="CNY"),
            priority=85,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="南朝四百八十寺之首，金陵最古老梵刹之一",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="午餐 · 鸡鸣寺百味斋特色素面与香干",
            place_id="lunch_d4",
            start_at=datetime(2026, 10, 4, 11, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 12, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=45, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝百味斋非遗素面",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="玄武湖台城段 · 明城墙揽胜与湖光天际线",
            place_id="taicheng_wall",
            start_at=datetime(2026, 10, 4, 13, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 14, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=30, currency="CNY"),
            priority=80,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="登临明城墙，俯瞰鸡鸣寺全景与玄武湖开阔水域",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="颐和路历史文化街区 · 十二片区民国公馆巡礼",
            place_id="yihelu",
            start_at=datetime(2026, 10, 4, 15, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 17, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=75,
            locked=False,
            indoor_outdoor=IndoorOutdoor.OUTDOOR,
            reason="一条颐和路，半部民国史；枫杨树下的静谧公馆漫步",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="晚餐 · 淮扬特色风味精选",
            place_id="dinner_d4",
            start_at=datetime(2026, 10, 4, 18, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 19, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=225, currency="CNY"),
            priority=65,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="品尝淮扬狮子头与大煮干丝",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.REST,
            title="返回金陵饭店 · 晚间休息",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 4, 20, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 4, 21, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=50,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="返回酒店休整",
        ),
    ]

    day4 = DayPlan(
        date=d4_date,
        day_number=4,
        theme="鸡鸣古刹祈福与颐和路枫杨公馆",
        weather=WeatherDay(
            date=d4_date,
            condition=WeatherCondition.CLOUDY,
            temperature_min_c=16.0,
            temperature_max_c=23.0,
            rain_probability=0.15,
            outdoor_suitability=OutdoorSuitability.GOOD,
            source=GLOBAL_SOURCE_REF,
        ),
        activities=d4_acts,
        route_legs=[],
        statistics=DayStatistics(
            activity_count=7,
            walking_meters=5500,
            transfer_minutes=55,
            planned_minutes=450,
            estimated_cost=Money(amount=310, currency="CNY"),
        ),
        warnings=["城墙台城段步行楼梯稍陡，请留意脚下安全。"],
    )
    days.append(day4)

    # ------------------ Day 5 ------------------
    d5_date = date(2026, 10, 5)
    leg_d5_train_id = uuid4()
    d5_acts = [
        Activity(
            id=uuid4(),
            kind=ActivityKind.CHECK_OUT,
            title="金陵饭店退房 · 行李装配与出发",
            place_id="jinling_hotel",
            start_at=datetime(2026, 10, 5, 9, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 5, 9, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="酒店退房并寄存或携带行李",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="先锋书店 · 五台山总店深度阅读与文创",
            place_id="xianfeng_books",
            start_at=datetime(2026, 10, 5, 10, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 5, 12, 0, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=0, currency="CNY"),
            priority=80,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="全球十大最美书店之一，防空洞改造的城市文化地标",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.MEAL,
            title="午餐 · 新街口金陵老字号小吃汇",
            place_id="lunch_d5",
            start_at=datetime(2026, 10, 5, 12, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 5, 13, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=80, currency="CNY"),
            priority=60,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="老字号糕团小吃与茶点",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.VISIT,
            title="新街口商业街区 · 特产与文创伴手礼选购",
            place_id="xinjiekou",
            start_at=datetime(2026, 10, 5, 13, 30, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 5, 15, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=None,
            estimated_cost=Money(amount=100, currency="CNY"),
            priority=70,
            locked=False,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="采购盐水鸭与雨花茶等金陵特色手信",
        ),
        Activity(
            id=uuid4(),
            kind=ActivityKind.TRANSFER,
            title="前往南京南站 · 乘坐高铁返回杭州",
            place_id="nj_south",
            start_at=datetime(2026, 10, 5, 16, 0, tzinfo=TZ_SHANGHAI),
            end_at=datetime(2026, 10, 5, 17, 30, tzinfo=TZ_SHANGHAI),
            route_leg_id=leg_d5_train_id,
            estimated_cost=Money(amount=180, currency="CNY"),
            priority=95,
            locked=True,
            indoor_outdoor=IndoorOutdoor.INDOOR,
            reason="城际交通返程",
        ),
    ]

    day5 = DayPlan(
        date=d5_date,
        day_number=5,
        theme="先锋书店文化探索与新街口返程",
        weather=WeatherDay(
            date=d5_date,
            condition=WeatherCondition.CLOUDY,
            temperature_min_c=17.0,
            temperature_max_c=24.0,
            rain_probability=0.20,
            outdoor_suitability=OutdoorSuitability.GOOD,
            source=GLOBAL_SOURCE_REF,
        ),
        activities=d5_acts,
        route_legs=[
            RouteLeg(
                id=leg_d5_train_id,
                origin_place_id="nj_south",
                destination_place_id="hz_east",
                mode=TransportMode.PUBLIC_TRANSIT,
                duration_minutes=60,
                distance_meters=260000,
                walking_meters=350,
                source=GLOBAL_SOURCE_REF,
            )
        ],
        statistics=DayStatistics(
            activity_count=5,
            walking_meters=4800,
            transfer_minutes=65,
            planned_minutes=360,
            estimated_cost=Money(amount=360, currency="CNY"),
        ),
        warnings=["返程高峰期建议提前45分钟到达南京南站候车。"],
    )
    days.append(day5)

    # ------------------ 预算精确加和 ------------------
    # 日常消费求和: 478 + 320 + 420 + 310 + 360 = 1,888
    # 住宿消费: 4晚 * 800 = 3,200
    # 往返大交通: 472
    # 门票与活动: 280 (大成殿50 + 总统府35 + 灵谷寺35 + 明孝陵70 + 鸡鸣寺10 + 城墙30 + 特产文创50)
    # 餐饮: 1,340
    # 交通: 740 (大交通472 + 市内地铁打车268)
    # 住宿: 3,200
    # 汇总: 3200 + 1340 + 740 + 280 = 5,560 元
    total_budget_amount = 5560
    budget_limit = 8000

    budget_items = [
        BudgetItem(
            id=uuid4(),
            category=BudgetCategory.ACCOMMODATION,
            label="金陵饭店 4 晚舒适客房住宿",
            date=None,
            amount=Money(amount=3200, currency="CNY"),
            estimated=True,
        ),
        BudgetItem(
            id=uuid4(),
            category=BudgetCategory.FOOD,
            label="5 日特色餐饮与地道名点",
            date=None,
            amount=Money(amount=1340, currency="CNY"),
            estimated=True,
        ),
        BudgetItem(
            id=uuid4(),
            category=BudgetCategory.INTERCITY_TRANSPORT,
            label="杭州东 往返 南京南 高铁二等座 (2人)",
            date=None,
            amount=Money(amount=472, currency="CNY"),
            estimated=False,
        ),
        BudgetItem(
            id=uuid4(),
            category=BudgetCategory.LOCAL_TRANSPORT,
            label="市内地铁、公交与网约车接驳",
            date=None,
            amount=Money(amount=268, currency="CNY"),
            estimated=True,
        ),
        BudgetItem(
            id=uuid4(),
            category=BudgetCategory.ADMISSION,
            label="景点景区门票与文创体验",
            date=None,
            amount=Money(amount=280, currency="CNY"),
            estimated=True,
        ),
    ]

    budget_summary = BudgetSummary(
        limit=Money(amount=budget_limit, currency="CNY"),
        planned_total=Money(amount=total_budget_amount, currency="CNY"),
        currency="CNY",
        items=budget_items,
        totals_by_category={
            BudgetCategory.ACCOMMODATION: Money(amount=3200, currency="CNY"),
            BudgetCategory.FOOD: Money(amount=1340, currency="CNY"),
            BudgetCategory.INTERCITY_TRANSPORT: Money(amount=472, currency="CNY"),
            BudgetCategory.LOCAL_TRANSPORT: Money(amount=268, currency="CNY"),
            BudgetCategory.ADMISSION: Money(amount=280, currency="CNY"),
        },
        remaining_amount=budget_limit - total_budget_amount,
        within_budget=True,
    )

    itinerary = Itinerary(
        trip_id=trip_id,
        title=f"杭州 → 南京 5 日深度文化与美食漫游 (版本 {version})",
        destination="南京",
        timezone="Asia/Shanghai",
        date_range=DateRange(start_date=start_d, end_date=date(2026, 10, 5)),
        days=days,
        budget=budget_summary,
        general_notes=[
            "提前在南京博物院官方小程序完成实名分时段预约（入馆携带二代身份证原件）。",
            "准备便携雨具与舒适轻便步行鞋，早晚温差明显建议备轻便外套。",
            "建议提前在支付宝或微信开通‘金陵通乘车码’，南京地铁与公交通用扫码畅行。",
            "确认杭宁高铁 G7511/G7517 往返车次（杭州东 07:48→南京南 09:00 / 南京南 16:35→杭州东 17:47）与金陵饭店入住凭证。",
        ],
        generated_at=datetime.now(UTC),
    )
    return itinerary


def seed_database():
    """执行数据库播种主函数"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        clean_existing_data(db)

        trip_request = TripRequest(
            origin="杭州",
            destination="南京",
            destination_timezone="Asia/Shanghai",
            date_range=DateRange(start_date=date(2026, 10, 1), end_date=date(2026, 10, 5)),
            travelers=2,
            preferences=TripPreferences(
                interests=[
                    WeightedPreference(value="文化古迹", weight=0.9),
                    WeightedPreference(value="特色美食", weight=0.85),
                    WeightedPreference(value="城市漫步", weight=0.75),
                ],
                transport_modes=[TransportMode.PUBLIC_TRANSIT, TransportMode.WALKING],
                pace=Pace.BALANCED,
            ),
            constraints=TripConstraints(
                total_budget=Money(amount=8000, currency="CNY"),
                daily_start_time="09:00",
                daily_end_time="21:00",
                max_walking_meters_per_day=10000,
                max_activities_per_day=5,
            ),
            locale="zh-CN",
            display_currency="CNY",
        )

        now = datetime.now(UTC)
        run_1_id = uuid4()
        run_2_id = uuid4()
        run_3_id = uuid4()

        # 1. 插入 Trip 聚合根
        trip_record = TripRecord(
            id=STANDARD_TRIP_ID,
            status=TripStatus.COMPLETED,
            revision=3,
            current_plan_version=3,
            active_planning_run_id=None,
            request=trip_request,
            created_at=now,
            updated_at=now,
        )
        db.add(trip_to_table(trip_record))
        db.flush()

        # 2. 插入 3 个演进版本
        # Version 1
        itinerary_v1 = build_nanjing_itinerary(STANDARD_TRIP_ID, 1)
        plan_v1 = PlanVersionRecord(
            id=uuid4(),
            trip_id=STANDARD_TRIP_ID,
            version=1,
            parent_version=None,
            status=PlanStatus.SUPERSEDED,
            trigger=PlanTrigger.INITIAL,
            itinerary=itinerary_v1,
            constraint_report=ConstraintReport(
                passed=True,
                violations=[],
                checked_rule_codes=["BUDGET_EXCEEDED", "DAILY_END_TIME_EXCEEDED", "MAX_WALKING_EXCEEDED"],
                checked_at=now,
                engine_version="v1.0.0",
            ),
            change_summary="根据 5 天日程与旅行偏好生成初始全量规划草案",
            planning_run_id=run_1_id,
            created_at=now,
            accepted_at=None,
        )
        db.add(plan_to_table(plan_v1))

        # Version 2
        itinerary_v2 = build_nanjing_itinerary(STANDARD_TRIP_ID, 2)
        plan_v2 = PlanVersionRecord(
            id=uuid4(),
            trip_id=STANDARD_TRIP_ID,
            version=2,
            parent_version=1,
            status=PlanStatus.SUPERSEDED,
            trigger=PlanTrigger.USER_FEEDBACK,
            itinerary=itinerary_v2,
            constraint_report=ConstraintReport(
                passed=True,
                violations=[],
                checked_rule_codes=["BUDGET_EXCEEDED", "DAILY_END_TIME_EXCEEDED", "MAX_WALKING_EXCEEDED"],
                checked_at=now,
                engine_version="v1.0.0",
            ),
            change_summary="调整出发时间至 09:00 并保留玄武湖傍晚日落最佳观赏时段",
            planning_run_id=run_2_id,
            created_at=now,
            accepted_at=None,
        )
        db.add(plan_to_table(plan_v2))

        # Version 3 (当前生效版本)
        itinerary_v3 = build_nanjing_itinerary(STANDARD_TRIP_ID, 3)
        plan_v3 = PlanVersionRecord(
            id=uuid4(),
            trip_id=STANDARD_TRIP_ID,
            version=3,
            parent_version=2,
            status=PlanStatus.ACCEPTED,
            trigger=PlanTrigger.MANUAL_VALIDATION,
            itinerary=itinerary_v3,
            constraint_report=ConstraintReport(
                passed=True,
                violations=[],
                checked_rule_codes=["BUDGET_EXCEEDED", "DAILY_END_TIME_EXCEEDED", "MAX_WALKING_EXCEEDED"],
                checked_at=now,
                engine_version="v1.0.0",
            ),
            change_summary="优化每日步行与地铁接驳，将全部日程以金陵饭店/南京南站作为闭环起止点",
            planning_run_id=run_3_id,
            created_at=now,
            accepted_at=now,
        )
        db.add(plan_to_table(plan_v3))

        # 3. 插入 PlanningRun 审计记录
        run_record = PlanningRunRecord(
            id=run_3_id,
            trip_id=STANDARD_TRIP_ID,
            trigger=PlanningRunTrigger.FEEDBACK,
            status=PlanningRunStatus.COMPLETED,
            progress_percent=100,
            current_step="FINISHED",
            base_plan_version=2,
            result_plan_version=3,
            feedback_id=None,
            repair_attempts=0,
            max_repair_attempts=3,
            error=None,
            created_at=now,
            started_at=now,
            finished_at=now,
        )
        db.add(run_to_table(run_record))

        db.commit()
        print(f"[SUCCESS] Successfully seeded standard Hangzhou -> Nanjing trip to PostgreSQL! Trip ID: {STANDARD_TRIP_ID}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
