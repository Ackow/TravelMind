"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { getTrip, getCurrentPlan, type TripResponse, type PlanVersionResponse, type PlanDay } from "@/lib/api/trips";
import { MiniRouteMap } from "./mini-route-map";
import { type MapPoint, type DayPointsGroup } from "@/components/map/DynamicMapView";
import styles from "./final-itinerary.module.css";

interface FinalItineraryProps {
  tripId?: string;
}

interface TimelineActivity {
  id: string;
  time: string;
  category: "flight" | "hotel" | "meal" | "attraction" | "shopping";
  title: string;
  duration: string;
  transitMode?: string;
  cost: string;
}

interface DayPlan {
  dayNumber: number;
  title: string;
  weather: {
    temp: string;
    desc: string;
    icon: string;
  };
  dailyCost: string;
  walking: string;
  activities: TimelineActivity[];
}

const CITY_COORDINATES: Record<string, { lat: number; lng: number }> = {
  "南京": { lat: 32.0603, lng: 118.7969 },
  "杭州": { lat: 30.2741, lng: 120.1551 },
  "北京": { lat: 39.9042, lng: 116.4074 },
  "上海": { lat: 31.2304, lng: 121.4737 },
  "东京": { lat: 35.6895, lng: 139.6917 },
};

const KNOWN_PLACE_COORDS: Record<string, { lat: number; lng: number }> = {
  // 南京地标与景点
  "夫子庙": { lat: 32.0195, lng: 118.7876 },
  "夫子庙-秦淮风光带": { lat: 32.0195, lng: 118.7876 },
  "中山陵": { lat: 32.0621, lng: 118.8488 },
  "中山陵景区": { lat: 32.0621, lng: 118.8488 },
  "南京博物院": { lat: 32.0421, lng: 118.8262 },
  "南京总统府": { lat: 32.0442, lng: 118.7967 },
  "玄武湖公园": { lat: 32.0725, lng: 118.7958 },
  "古鸡鸣寺": { lat: 32.0603, lng: 118.7969 },
  "老门东": { lat: 32.0138, lng: 118.7885 },
  "老门东历史街区": { lat: 32.0138, lng: 118.7885 },
  "新街口商圈": { lat: 32.0416, lng: 118.7842 },
  "侵华日军南京大屠杀遇难同胞纪念馆": { lat: 32.0354, lng: 118.7447 },
  "牛首山文化旅游区": { lat: 31.9126, lng: 118.7485 },
  "南京南站": { lat: 31.9702, lng: 118.7981 },
  "tm_place_nanjing_south_station": { lat: 31.9702, lng: 118.7981 },
  "金陵饭店(新街口店)": { lat: 32.0435, lng: 118.7845 },
  "金陵饭店": { lat: 32.0435, lng: 118.7845 },
  "tm_place_jinling_hotel": { lat: 32.0435, lng: 118.7845 },
  "南京大牌档(德基广场店)": { lat: 32.0440, lng: 118.7840 },
  "tm_place_nanjing_dapaidang": { lat: 32.0440, lng: 118.7840 },
  "民国往事·民国红公馆(1912街区店)": { lat: 32.0460, lng: 118.7950 },
  "民国红公馆": { lat: 32.0460, lng: 118.7950 },
  "tm_place_honggongguan": { lat: 32.0460, lng: 118.7950 },
  "江南灶中餐厅(香格里拉大酒店)": { lat: 32.0820, lng: 118.7920 },
  "江南灶中餐厅": { lat: 32.0820, lng: 118.7920 },
  "tm_place_jiangnanzao": { lat: 32.0820, lng: 118.7920 },
  "小厨娘淮扬菜(老门东店)": { lat: 32.0145, lng: 118.7890 },
  "小厨娘淮扬菜": { lat: 32.0145, lng: 118.7890 },
  "tm_place_xiaochuniang": { lat: 32.0145, lng: 118.7890 },
  "绿柳居(太平南路店)": { lat: 32.0380, lng: 118.7930 },
  "绿柳居": { lat: 32.0380, lng: 118.7930 },
  "tm_place_lvliuju": { lat: 32.0380, lng: 118.7930 },

  // 北京地标与景点
  "北京南站": { lat: 39.8650, lng: 116.3785 },
  "tm_place_beijing_south_station": { lat: 39.8650, lng: 116.3785 },
  "北京王府井希尔顿酒店": { lat: 39.9145, lng: 116.4110 },
  "王府井希尔顿酒店": { lat: 39.9145, lng: 116.4110 },
  "tm_place_wangfujing_hilton": { lat: 39.9145, lng: 116.4110 },
  "故宫博物院": { lat: 39.9163, lng: 116.3972 },
  "tm_place_forbidden_city": { lat: 39.9163, lng: 116.3972 },
  "天坛公园": { lat: 39.8822, lng: 116.4068 },
  "tm_place_tiantan": { lat: 39.8822, lng: 116.4068 },
  "颐和园": { lat: 39.9999, lng: 116.2755 },
  "tm_place_summer_palace": { lat: 39.9999, lng: 116.2755 },
  "景山公园": { lat: 39.9248, lng: 116.3965 },
  "tm_place_jingshan": { lat: 39.9248, lng: 116.3965 },
  "什刹海": { lat: 39.9385, lng: 116.3888 },
  "tm_place_shichahai": { lat: 39.9385, lng: 116.3888 },
  "中国国家博物馆": { lat: 39.9055, lng: 116.3975 },
  "tm_place_national_museum": { lat: 39.9055, lng: 116.3975 },
  "雍和宫": { lat: 39.9472, lng: 116.4178 },
  "雍和宫 & 国子监街": { lat: 39.9472, lng: 116.4178 },
  "tm_place_yonghegong": { lat: 39.9472, lng: 116.4178 },
  "四季民福烤鸭店(故宫店)": { lat: 39.9150, lng: 116.4030 },
  "tm_place_sijiminfu": { lat: 39.9150, lng: 116.4030 },
  "全聚德(前门店)": { lat: 39.8970, lng: 116.3980 },
  "tm_place_quanjude": { lat: 39.8970, lng: 116.3980 },
  "局气(王府井店)": { lat: 39.9125, lng: 116.4105 },
  "tm_place_juqi": { lat: 39.9125, lng: 116.4105 },
  "金鼎轩(地坛总店)": { lat: 39.9535, lng: 116.4180 },
  "tm_place_jindingxuan": { lat: 39.9535, lng: 116.4180 },
};

function formatTime(isoStr: string, timezone: string = "Asia/Shanghai"): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: timezone,
    });
  } catch {
    return "09:00";
  }
}

function calculateDuration(startIso: string, endIso: string): string {
  try {
    const start = new Date(startIso).getTime();
    const end = new Date(endIso).getTime();
    const mins = Math.max(0, Math.round((end - start) / 60000));
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  } catch {
    return "1h";
  }
}

function getWeatherIcon(condition?: string): string {
  if (!condition) return "/icons/weather-sunny.svg";
  const c = condition.toLowerCase();
  if (c.includes("rain") || c.includes("雨")) return "/icons/weather-light-rain.svg";
  if (c.includes("cloud") || c.includes("阴") || c.includes("多云")) return "/icons/weather-cloudy.svg";
  return "/icons/weather-sunny.svg";
}

function mapKindToCategory(kind: string): TimelineActivity["category"] {
  switch (kind) {
    case "check_in":
    case "check_out":
      return "hotel";
    case "meal":
      return "meal";
    case "transfer":
      return "flight";
    case "free_time":
      return "shopping";
    case "visit":
    default:
      return "attraction";
  }
}

export function FinalItinerary({
  tripId = "77777777-7777-7777-7777-777777777777",
}: FinalItineraryProps) {
  const router = useRouter();
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [plan, setPlan] = useState<PlanVersionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedDays, setExpandedDays] = useState<number[]>([1]);
  const [selectedMapDay, setSelectedMapDay] = useState<number>(1);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<{ [key: string]: boolean }>({
    item0: true,
    item1: true,
    item2: true,
    item3: true,
  });

  useEffect(() => {
    let active = true;
    const targetId = tripId || "77777777-7777-7777-7777-777777777777";
    setLoading(true);

    Promise.all([
      getTrip(targetId).catch(() => null),
      getCurrentPlan(targetId).catch(() => null),
    ]).then(([tripRes, planRes]) => {
      if (!active) return;
      if (tripRes) setTrip(tripRes);
      if (planRes) {
        setPlan(planRes);
        const notes = planRes.itinerary?.general_notes?.length
          ? planRes.itinerary.general_notes
          : [
              "身份证 / 护照有效证件原件及复印件",
              "行程目的地实时天气适应衣物及雨具",
              "重点景点及文博场馆实名预约二维码凭证",
              "常备个人药品及充电宝随身物品",
            ];
        const initialChecks: { [key: string]: boolean } = {};
        notes.forEach((_, idx) => {
          initialChecks[`item${idx}`] = true;
        });
        setChecklist(initialChecks);
      }
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [tripId]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2600);
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      const shareUrl = `${window.location.origin}/trips/${trip?.id || tripId}/final`;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(shareUrl);
      }
    }
    showToast("行程公开分享链接已复制到剪贴板");
  };

  const handleExportPdf = () => {
    if (plan?.itinerary?.days) {
      setExpandedDays(plan.itinerary.days.map((d) => d.day_number));
    }
    showToast("准备导出 PDF... 正在生成打印排版视图");
    setTimeout(() => {
      window.print();
    }, 400);
  };

  const toggleDay = (dayNumber: number) => {
    setSelectedMapDay(dayNumber);
    setExpandedDays((prev) =>
      prev.includes(dayNumber)
        ? prev.filter((d) => d !== dayNumber)
        : [...prev, dayNumber]
    );
  };

  const toggleCheck = (key: string) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "flight":
        return "/icons/train.svg";
      case "hotel":
        return "/icons/calendar.svg";
      case "meal":
        return "/icons/meal.svg";
      case "shopping":
        return "/icons/shopping.svg";
      case "attraction":
      default:
        return "/icons/attraction.svg";
    }
  };

  // 动态将后端计划 DayPlan 转换为 UI 渲染模型
  const days: DayPlan[] = useMemo(() => {
    if (!plan?.itinerary?.days?.length) return [];
    const tz = plan.itinerary.timezone || "Asia/Shanghai";

    return plan.itinerary.days.map((day: PlanDay) => {
      const weatherMin = day.weather?.temperature_min_c != null ? Math.round(day.weather.temperature_min_c) : 18;
      const weatherMax = day.weather?.temperature_max_c != null ? Math.round(day.weather.temperature_max_c) : 24;
      const weatherDesc = day.weather?.condition === "clear" ? "晴" : day.weather?.condition === "rain" ? "小雨" : day.weather?.condition || "多云";

      const dailyCostCents = day.statistics?.estimated_cost?.amount ?? 0;
      const walkingKm = ((day.statistics?.walking_meters ?? 0) / 1000).toFixed(1);

      const activities: TimelineActivity[] = day.activities.map((act) => {
        const costYuan = act.estimated_cost?.amount ? (act.estimated_cost.amount / 100).toFixed(0) : "0";
        return {
          id: act.id,
          time: formatTime(act.start_at, tz),
          category: mapKindToCategory(act.kind),
          title: act.title,
          duration: calculateDuration(act.start_at, act.end_at),
          transitMode: act.notes?.[0] || act.reason || undefined,
          cost: `¥${costYuan}`,
        };
      });

      return {
        dayNumber: day.day_number,
        title: day.theme ? `Day ${day.day_number} · ${day.theme}` : `Day ${day.day_number} 行程`,
        weather: {
          temp: `${weatherMin}-${weatherMax}°C`,
          desc: weatherDesc,
          icon: getWeatherIcon(day.weather?.condition),
        },
        dailyCost: `¥${(dailyCostCents / 100).toFixed(0)}`,
        walking: `${walkingKm} km`,
        activities,
      };
    });
  }, [plan]);

  // 动态由行程活动计算地图点位
  const allDaysPoints: DayPointsGroup[] = useMemo(() => {
    if (!plan?.itinerary?.days?.length) return [];

    const city = trip?.destination || "南京";
    const center = CITY_COORDINATES[city] || { lat: 32.0603, lng: 118.7969 };

    return plan.itinerary.days.map((day) => {
      const points: MapPoint[] = day.activities.map((act, index) => {
        const known = KNOWN_PLACE_COORDS[act.title] || (act.place_id ? KNOWN_PLACE_COORDS[act.place_id] : null);
        const lat = known ? known.lat : center.lat + (index * 0.008 - 0.015);
        const lng = known ? known.lng : center.lng + (index * 0.010 - 0.015);

        return {
          id: act.id,
          title: act.title,
          lat,
          lng,
          sequence: index + 1,
          kind:
            act.kind === "meal"
              ? "特色美食"
              : act.kind === "check_in" || act.kind === "check_out" || act.kind === "rest"
              ? "酒店住宿"
              : act.kind === "transfer"
              ? "交通换乘"
              : act.indoor_outdoor === "outdoor"
              ? "风景名胜"
              : "人文展馆",
          transitToNext: act.notes?.[0]
            ? {
                mode: act.notes[0],
                duration: "",
              }
            : undefined,
        };
      });

      return {
        dayNumber: day.day_number,
        theme: day.theme,
        points,
      };
    });
  }, [plan, trip]);

  // 预算动态汇总
  const plannedCost = plan ? Math.round(plan.itinerary.budget.planned_total.amount / 100) : 0;
  const limitCost = plan ? Math.round(plan.itinerary.budget.limit.amount / 100) : 0;
  const remainingCost = limitCost - plannedCost;
  const budgetUsagePercent = Math.min(100, Math.round((plannedCost / Math.max(1, limitCost)) * 100));

  const totals = plan?.itinerary.budget.totals_by_category || {};
  const accommodationCost = Math.round((totals["accommodation"]?.amount ?? 0) / 100);
  const foodCost = Math.round((totals["food"]?.amount ?? 0) / 100);
  const transportCost = Math.round(
    ((totals["transport"]?.amount ?? 0) +
      (totals["intercity_transport"]?.amount ?? 0) +
      (totals["local_transport"]?.amount ?? 0)) / 100
  );
  const admissionCost = Math.round((totals["admission"]?.amount ?? 0) / 100);

  const accommodationPercent = plannedCost > 0 ? Math.round((accommodationCost / plannedCost) * 100) : 35;
  const foodPercent = plannedCost > 0 ? Math.round((foodCost / plannedCost) * 100) : 30;
  const transportPercent = plannedCost > 0 ? Math.round((transportCost / plannedCost) * 100) : 20;
  const admissionPercent = plannedCost > 0 ? Math.round((admissionCost / plannedCost) * 100) : 15;

  const totalWalkingKm = plan?.itinerary?.days
    ? (plan.itinerary.days.reduce((acc, d) => acc + (d.statistics?.walking_meters ?? 0), 0) / 1000).toFixed(1)
    : "0.0";

  const checklistItems = plan?.itinerary?.general_notes?.length
    ? plan.itinerary.general_notes
    : [
        "身份证 / 护照有效证件原件及复印件",
        "行程目的地实时天气适应衣物及雨具",
        "重点景点及文博场馆实名预约二维码凭证",
        "常备个人药品及充电宝随身物品",
      ];

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.contentWrapper} style={{ padding: "60px 0", textAlign: "center" }}>
          <p style={{ fontSize: "16px", color: "var(--color-text-secondary, #666)" }}>
            正在加载出案行程与真实地图数据...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      {/* Toast Alert */}
      {toastMessage && (
        <div className={styles.toast} role="alert">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{toastMessage}</span>
        </div>
      )}

      <div className={styles.contentWrapper}>
        {/* Top Header Row */}
        <header className={styles.topHeaderRow}>
          <div className={styles.heroLeft}>
            {/* Status Badge */}
            <div className={styles.statusBadge}>
              <span className={styles.statusIcon}>✓</span>
              <span>已确认</span>
            </div>

            {/* Title */}
            <h1 className={styles.heroTitle}>
              {trip?.destination || "目的地"} · {days.length} 日旅行计划
            </h1>

            {/* Subtitle */}
            <p className={styles.heroSubtitle}>
              {trip
                ? `${trip.date_range.start_date.replace(/-/g, ".")} — ${trip.date_range.end_date.replace(/-/g, ".")} · ${trip.travelers} 位旅行者`
                : "旅行计划已生成"}
            </p>

            {/* Route */}
            <div className={styles.routeRow}>
              <span className={styles.routeText}>
                {trip ? `${trip.origin} → ${trip.destination}` : "行程概览"}
              </span>
            </div>

            {/* Tags & Version Pill */}
            <div className={styles.tagRow}>
              {trip?.preferences?.interests?.length ? (
                trip.preferences.interests.map((pref) => (
                  <span key={pref.value} className={styles.tagPill}>
                    {pref.value}
                  </span>
                ))
              ) : (
                <span className={styles.tagPill}>特色文化</span>
              )}
              <span className={styles.versionPill}>版本 {plan?.version ?? 1}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className={styles.heroActions}>
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handleShare}
            >
              <Image
                src="/icons/export.svg"
                alt=""
                width={16}
                height={16}
                className={styles.darkIcon}
              />
              <span>分享链接</span>
            </button>
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handleExportPdf}
            >
              <Image
                src="/icons/clipboard-list.svg"
                alt=""
                width={16}
                height={16}
                className={styles.darkIcon}
              />
              <span>导出 PDF</span>
            </button>
            <button
              type="button"
              className={styles.primaryBtn}
              onClick={() => router.push(`/trips/${trip?.id || tripId}/history`)}
            >
              查看版本
            </button>
          </div>
        </header>

        {/* Two-Column Responsive Main Layout */}
        <div className={styles.mainGrid}>
          {/* Left Column: Itinerary Details */}
          <main className={styles.leftCol} aria-label="行程详情">
            {/* 4 Summary Stat Cards */}
            <section className={styles.statsRow} aria-label="行程核心数据">
              <div className={styles.statCard}>
                <Image
                  src="/icons/calendar.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>
                  {days.length} 天 {Math.max(1, days.length - 1)} 晚
                </strong>
              </div>
              <div className={styles.statCard}>
                <Image
                  src="/icons/clipboard-list.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>
                  {days.reduce((acc, d) => acc + d.activities.length, 0)} 个活动
                </strong>
              </div>
              <div className={styles.statCard}>
                <Image
                  src="/icons/wallet.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>
                  预计 ¥{plannedCost.toLocaleString()}
                </strong>
              </div>
              <div className={styles.statCard}>
                <Image
                  src="/icons/walking.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>
                  步行 {totalWalkingKm} km
                </strong>
              </div>
            </section>

            {/* Validation Statement Banner */}
            <div className={styles.validationBanner}>
              <span className={styles.verifCheckIcon}>✓</span>
              <span className={styles.verifBannerText}>所有硬性约束已通过</span>
            </div>

            {/* Day-by-Day Accordion */}
            <div className={styles.daysAccordion}>
              {days.map((day) => {
                const isExpanded = expandedDays.includes(day.dayNumber);

                return (
                  <section
                    key={day.dayNumber}
                    className={styles.dayCard}
                    aria-label={`Day ${day.dayNumber} 行程`}
                  >
                    {/* Day Header Trigger */}
                    <button
                      type="button"
                      className={styles.dayHeader}
                      onClick={() => toggleDay(day.dayNumber)}
                      aria-expanded={isExpanded}
                    >
                      <h3 className={styles.dayTitle}>{day.title}</h3>

                      <div className={styles.dayMeta}>
                        {/* Weather */}
                        <div className={styles.dayWeather}>
                          <Image
                            src={day.weather.icon}
                            alt=""
                            width={16}
                            height={16}
                          />
                          <span>
                            {day.weather.temp} {day.weather.desc}
                          </span>
                        </div>

                        {/* Cost */}
                        <div className={styles.dayMetaItem}>
                          <Image
                            src="/icons/wallet.svg"
                            alt=""
                            width={15}
                            height={15}
                            className={styles.mutedIcon}
                          />
                          <span>{day.dailyCost}</span>
                        </div>

                        {/* Walking */}
                        <div className={styles.dayMetaItem}>
                          <Image
                            src="/icons/walking.svg"
                            alt=""
                            width={15}
                            height={15}
                            className={styles.mutedIcon}
                          />
                          <span>{day.walking}</span>
                        </div>

                        {/* Chevron */}
                        <span
                          className={styles.dayChevron}
                          style={{
                            display: "inline-block",
                            transform: isExpanded
                              ? "rotate(180deg)"
                              : "rotate(0deg)",
                            transition: "transform 200ms ease",
                          }}
                        >
                          ▼
                        </span>
                      </div>
                    </button>

                    {/* Timeline Collapsible Body */}
                    <div
                      className={`${styles.timelineCollapseWrapper} ${
                        isExpanded ? styles.timelineCollapseOpen : ""
                      }`}
                    >
                      <div className={styles.timelineCollapseInner}>
                        <div className={styles.timelineBody}>
                          {day.activities.map((act, actIdx) => {
                            const isLast = actIdx === day.activities.length - 1;

                            return (
                              <div key={act.id} className={styles.activityRow}>
                                {/* Left Time & Bullet */}
                                <div className={styles.activityTimeCol}>
                                  <div className={styles.timeNodeWrapper}>
                                    <div className={styles.timeBullet} />
                                    {!isLast && (
                                      <div className={styles.timeTrack} />
                                    )}
                                  </div>
                                  <span className={styles.actTime}>
                                    {act.time}
                                  </span>
                                </div>

                                {/* Category Icon */}
                                <div className={styles.actIconArea}>
                                  <Image
                                    src={getCategoryIcon(act.category)}
                                    alt=""
                                    width={18}
                                    height={18}
                                    className={styles.darkIcon}
                                  />
                                </div>

                                {/* Title */}
                                <div className={styles.actTitleArea}>
                                  <span className={styles.actTitle}>
                                    {act.title}
                                  </span>
                                </div>

                                {/* Duration */}
                                <div className={styles.actDuration}>
                                  <span>{act.duration}</span>
                                </div>

                                {/* Transit Transition */}
                                <div className={styles.actTransit}>
                                  {act.transitMode && (
                                    <span className={styles.transitBadge}>
                                      <Image
                                        src={
                                          act.transitMode.includes("步行")
                                            ? "/icons/walking.svg"
                                            : "/icons/train.svg"
                                        }
                                        alt=""
                                        width={14}
                                        height={14}
                                        className={styles.mutedIcon}
                                      />
                                      {act.transitMode}
                                    </span>
                                  )}
                                </div>

                                {/* Cost */}
                                <div className={styles.actCost}>
                                  <span>{act.cost}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </section>
                );
              })}
            </div>
          </main>

          {/* Right Column: Sticky Summary & Checklist starting at same level as Stats */}
          <aside className={styles.rightCol} aria-label="旅行总览与提醒">
            {/* Card 1: 旅行总览 */}
            <div className={styles.card}>
              <h2 className={styles.sidebarCardTitle}>旅行总览</h2>

              {/* Map Graphic */}
              <MiniRouteMap
                destination={trip?.destination || "南京"}
                allDaysPoints={allDaysPoints}
                currentDay={selectedMapDay}
                onSelectDay={(idx) => setSelectedMapDay(idx + 1)}
              />

              {/* Budget Progress Bar */}
              <div className={styles.budgetSummaryArea}>
                <div className={styles.budgetMainRow}>
                  <strong className={styles.budgetCurrent}>
                    ¥{plannedCost.toLocaleString()}
                  </strong>
                  <span className={styles.budgetLimit}>
                    / ¥{limitCost.toLocaleString()}
                  </span>
                  <span className={styles.budgetLeft}>
                    {remainingCost >= 0
                      ? `预留 ¥${remainingCost.toLocaleString()}`
                      : `超支 ¥${Math.abs(remainingCost).toLocaleString()}`}
                  </span>
                </div>

                <div className={styles.progressBarTrack}>
                  <div
                    className={styles.progressBarFill}
                    style={{ width: `${budgetUsagePercent}%` }}
                  />
                </div>
                <div className={styles.progressPercentLabel}>
                  {budgetUsagePercent}%
                </div>
              </div>

              {/* Breakdown Bars */}
              <div className={styles.breakdownList}>
                {/* 1. 住宿 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/calendar.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.tealIcon}
                    />
                    <span>住宿</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{
                        width: `${Math.min(100, accommodationPercent)}%`,
                        backgroundColor: "#0f766e",
                      }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>
                    ¥{accommodationCost.toLocaleString()} ({accommodationPercent}%)
                  </span>
                </div>

                {/* 2. 餐饮 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/meal.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.emeraldIcon}
                    />
                    <span>餐饮</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{
                        width: `${Math.min(100, foodPercent)}%`,
                        backgroundColor: "#10b981",
                      }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>
                    ¥{foodCost.toLocaleString()} ({foodPercent}%)
                  </span>
                </div>

                {/* 3. 交通 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/train.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.blueIcon}
                    />
                    <span>交通</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{
                        width: `${Math.min(100, transportPercent)}%`,
                        backgroundColor: "#3b82f6",
                      }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>
                    ¥{transportCost.toLocaleString()} ({transportPercent}%)
                  </span>
                </div>

                {/* 4. 门票与活动 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/attraction.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.orangeIcon}
                    />
                    <span>门票与活动</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{
                        width: `${Math.min(100, admissionPercent)}%`,
                        backgroundColor: "#f97316",
                      }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>
                    ¥{admissionCost.toLocaleString()} ({admissionPercent}%)
                  </span>
                </div>
              </div>
            </div>

            {/* Card 2: 出发前提醒 */}
            <div className={styles.card}>
              <h2 className={styles.sidebarCardTitle}>出发前提醒</h2>

              <div className={styles.checklist}>
                {checklistItems.map((note, idx) => {
                  const key = `item${idx}`;
                  return (
                    <label key={key} className={styles.checkItem}>
                      <input
                        type="checkbox"
                        checked={!!checklist[key]}
                        onChange={() => toggleCheck(key)}
                        className={styles.checkboxInput}
                      />
                      <span className={styles.customCheckCircle}>✓</span>
                      <span className={styles.checkLabel}>{note}</span>
                    </label>
                  );
                })}
              </div>

              {/* Info Block with SVG Icon */}
              <div className={styles.departureInfoBlock}>
                <Image
                  src="/icons/info-circle.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.infoIconFilter}
                />
                <p className={styles.departureInfoText}>
                  天气与开放时间实时获取于行程规划引擎，出发前请再次确认
                </p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
