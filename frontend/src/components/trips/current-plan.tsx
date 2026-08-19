"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  getCurrentPlan,
  acceptPlanVersion,
  type PlanActivity,
  type PlanDay,
  type PlanVersionResponse,
  type TripResponse,
} from "@/lib/api/trips";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
import { DynamicMapView, type MapPoint } from "@/components/map/DynamicMapView";
import styles from "./current-plan.module.css";

const BUDGET_ROWS = [
  {
    key: "accommodation",
    label: "住宿",
    icon: "/icons/calendar.svg",
    color: "#14816f",
  },
  { key: "food", label: "餐饮", icon: "/icons/meal.svg", color: "#17907e" },
  {
    key: "local_transport",
    label: "交通",
    icon: "/icons/train.svg",
    color: "#5aa9e6",
  },
  {
    key: "admission",
    label: "门票",
    icon: "/icons/attraction.svg",
    color: "#ffb63f",
  },
] as const;

const CITY_CENTERS: Record<string, { lat: number; lng: number }> = {
  "南京": { lat: 32.0603, lng: 118.7969 },
  "杭州": { lat: 30.2741, lng: 120.1551 },
  "北京": { lat: 39.9042, lng: 116.4074 },
  "上海": { lat: 31.2304, lng: 121.4737 },
  "成都": { lat: 30.5728, lng: 104.0668 },
  "广州": { lat: 23.1291, lng: 113.2644 },
  "深圳": { lat: 22.5431, lng: 114.0579 },
  "苏州": { lat: 31.2989, lng: 120.5853 },
  "西安": { lat: 34.3416, lng: 108.9398 },
  "重庆": { lat: 29.5630, lng: 106.5516 },
  "武汉": { lat: 30.5928, lng: 114.3055 },
  "东京": { lat: 35.6895, lng: 139.6917 },
};

const PLACE_COORDINATES: Record<string, { lat: number; lng: number }> = {
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

  // 其他城市代表景点
  "西湖风景名胜区": { lat: 30.2428, lng: 120.1500 },
  "灵隐寺": { lat: 30.2415, lng: 120.1008 },
  "雷峰塔": { lat: 30.2312, lng: 120.1488 },
  "断桥残雪": { lat: 30.2592, lng: 120.1502 },
  "外滩": { lat: 31.2397, lng: 121.4900 },
  "东方明珠": { lat: 31.2397, lng: 121.4998 },
  "浅草寺": { lat: 35.7147, lng: 139.7966 },
  "东京晴空塔": { lat: 35.7100, lng: 139.8107 },
  "上野公园": { lat: 35.7141, lng: 139.7741 },
  "秋叶原电气街": { lat: 35.6983, lng: 139.7731 },
  "东京国立博物馆": { lat: 35.7189, lng: 139.7765 },
  "银座购物区": { lat: 35.6719, lng: 139.7648 },
  "涩谷十字路口": { lat: 35.6595, lng: 139.7005 },
  "新宿御苑": { lat: 35.6852, lng: 139.7100 },
  "明治神宫": { lat: 35.6764, lng: 139.6993 },
  "teamLab Planets": { lat: 35.6491, lng: 139.7898 },
  "筑地场外市场": { lat: 35.6655, lng: 139.7708 },
  "东京塔": { lat: 35.6586, lng: 139.7454 },
};

function formatMoney(amount: number, currency = "CNY") {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

function formatTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: timezone,
  }).format(new Date(value));
}

function dateParts(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return {
    short: new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
    }).format(date),
    full: new Intl.DateTimeFormat("zh-CN", {
      month: "long",
      day: "numeric",
      weekday: "long",
    }).format(date),
  };
}

function durationText(activity: PlanActivity) {
  const minutes = Math.round(
    (new Date(activity.end_at).getTime() -
      new Date(activity.start_at).getTime()) /
      60000,
  );
  return minutes >= 60 ? `${minutes / 60}h` : `${minutes} 分钟`;
}

function weatherIcon(day: PlanDay) {
  const rain = day.weather?.rain_probability ?? 0;
  if (rain >= 0.5) return "/icons/weather-light-rain.svg";
  if (rain >= 0.25) return "/icons/weather-partly-cloudy.svg";
  return "/icons/weather-sunny.svg";
}

function activityIcon(activity: PlanActivity) {
  if (activity.kind === "meal") return "/icons/meal.svg";
  if (activity.kind === "transfer") return "/icons/train.svg";
  if (activity.title.includes("博物馆") || activity.title.includes("美术馆"))
    return "/icons/museum.svg";
  return "/icons/attraction.svg";
}

function temperature(day: PlanDay) {
  return `${day.weather?.temperature_min_c ?? "--"}–${day.weather?.temperature_max_c ?? "--"}°C`;
}

export function CurrentPlan({ trip }: { trip: TripResponse }) {
  const [plan, setPlan] = useState<PlanVersionResponse | null>(null);
  const [selectedDay, setSelectedDay] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [openActivityId, setOpenActivityId] = useState<string | null>(null);
  const [constraintExpanded, setConstraintExpanded] = useState(false);
  const [acceptDialogOpen, setAcceptDialogOpen] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentPlan(trip.id)
      .then((result) => {
        if (active) {
          setPlan(result);
          setSelectedDay(0);
        }
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "读取计划失败");
      });
    return () => {
      active = false;
    };
  }, [trip.id]);

  const rainyDay = useMemo(
    () =>
      plan?.itinerary.days.find(
        (item) => (item.weather?.rain_probability ?? 0) >= 0.6,
      ),
    [plan],
  );

  function exportPlan() {
    if (!plan) return;
    const file = new Blob([JSON.stringify(plan, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(file);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${trip.destination}-行程版本${plan.version}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setToast("行程 JSON 已导出");
  }

  async function copyActivityName(title: string) {
    try {
      await navigator.clipboard.writeText(title);
      setToast(`已复制“${title}”`);
    } catch {
      setToast(`活动名称：${title}`);
    }
    setOpenActivityId(null);
  }
  if (error)
    return (
      <p className={styles.state} role="alert">
        {error}
      </p>
    );
  if (!plan) return <p className={styles.state}>正在读取旅行计划…</p>;

  const day = plan.itinerary.days[selectedDay] ?? plan.itinerary.days[0];
  const budget = plan.itinerary.budget;
  const budgetPercent = budget.limit.amount
    ? Math.min(
        100,
        Math.round((budget.planned_total.amount / budget.limit.amount) * 100),
      )
    : 0;
  const dayRain = Math.round((day.weather?.rain_probability ?? 0) * 100);
  const numberedActivities = day.activities.filter(
    (activity) => activity.kind !== "transfer",
  );

  const baseCenter = CITY_CENTERS[trip.destination] || { lat: 32.0603, lng: 118.7969 };
  const allDaysPoints = plan.itinerary.days.map((d) => {
    const acts = d.activities.filter((a) => a.kind !== "transfer");
    return {
      dayNumber: d.day_number,
      theme: d.theme,
      points: acts.map((a, idx) => {
        const coords = PLACE_COORDINATES[a.title] || {
          lat: baseCenter.lat + (((idx * 7) % 7) - 3) * 0.012,
          lng: baseCenter.lng + (((idx * 11) % 7) - 3) * 0.015,
        };
        return {
          id: a.id,
          title: a.title,
          lat: coords.lat,
          lng: coords.lng,
          sequence: idx + 1,
          kind: a.kind,
        };
      }),
    };
  });

  const mapPoints: MapPoint[] = allDaysPoints[selectedDay]?.points || [];

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <div>
          <PageBreadcrumb
            items={[
              { label: "我的旅行", href: "/" },
              { label: `${trip.destination} ${plan.itinerary.days.length} 日游` },
            ]}
          />
          <div className={styles.titleRow}>
            <h1>
              {trip.destination} {plan.itinerary.days.length} 日旅行草案
            </h1>
            <span>等待审阅</span>
          </div>
          <p className={styles.version}>版本 {plan.version} · 刚刚生成</p>
        </div>
        <div className={styles.heroActions}>
          <button
            className={styles.exportButton}
            onClick={exportPlan}
            type="button"
          >
            <Image src="/icons/export.svg" width={18} height={18} alt="" />
            导出
          </button>
        </div>
      </header>

      <section className={styles.workspace}>
        <div className={styles.alertBanner}>
          <Image
            src="/icons/warning-triangle.svg"
            width={22}
            height={22}
            alt=""
          />
          <span>
            {rainyDay
              ? `${dateParts(rainyDay.date).full}降雨概率较高，已将户外活动调整至其他日期`
              : "行程已结合天气与开放时间完成检查"}
          </span>
          <button
            type="button"
            onClick={() => {
              if (rainyDay) setSelectedDay(rainyDay.day_number - 1);
              else setToast("天气、开放时间和交通检查均已完成");
            }}
          >
            查看调整{" "}
            <Image
              src="/icons/chevron-right.svg"
              width={16}
              height={16}
              alt=""
            />
          </button>
        </div>

        <aside className={styles.dayColumn} aria-label="每日行程">
          <div className={styles.dayCards}>
            {plan.itinerary.days.map((item, index) => (
              <button
                className={
                  selectedDay === index ? styles.dayActive : styles.dayCard
                }
                key={item.date}
                type="button"
                onClick={() => setSelectedDay(index)}
              >
                <Image src={weatherIcon(item)} width={36} height={36} alt="" />
                <span className={styles.dayContent}>
                  <span>
                    Day {item.day_number} · {dateParts(item.date).short}
                  </span>
                  <strong>{item.theme}</strong>
                  <small>
                    {temperature(item)}{" "}
                    <b>
                      {formatMoney(
                        item.statistics.estimated_cost.amount,
                        item.statistics.estimated_cost.currency,
                      )}
                    </b>
                  </small>
                </span>
              </button>
            ))}
          </div>
          <div className={styles.totalBudget}>
            <span>
              总预算已使用 <strong>{budgetPercent}%</strong>
            </span>
            <div>
              <i style={{ width: `${budgetPercent}%` }} />
            </div>
            <p>
              {formatMoney(budget.planned_total.amount, budget.currency)} /{" "}
              {formatMoney(budget.limit.amount, budget.currency)}
            </p>
          </div>
        </aside>

        <section className={styles.timelinePanel}>
          <header className={styles.timelineHeader}>
            <h2>
              Day {day.day_number} · {dateParts(day.date).full}
            </h2>
            <div>
              <span className={styles.weatherFact}>
                <Image src={weatherIcon(day)} width={27} height={27} alt="" />
                {temperature(day)} · 降雨 {dayRain}%
              </span>
              <span className={styles.indoorBadge}>
                {day.weather?.outdoor_suitability === "poor"
                  ? "室内为主"
                  : "灵活安排"}
              </span>
              <span className={styles.walkBadge}>
                步行 {(day.statistics.walking_meters / 1000).toFixed(1)} km
              </span>
            </div>
          </header>
          <ol className={styles.timeline}>
            {day.activities.map((activity) => {
              const transfer = activity.kind === "transfer";
              const route = activity.route_leg_id
                ? day.route_legs.find(
                    (item) => item.id === activity.route_leg_id,
                  )
                : null;
              const nodeNumber = transfer
                ? ""
                : numberedActivities.findIndex(
                    (item) => item.id === activity.id,
                  ) + 1;
              return (
                <li
                  className={
                    transfer ? styles.transferNode : styles.activityNode
                  }
                  key={activity.id}
                >
                  <time>
                    {formatTime(activity.start_at, plan.itinerary.timezone)}
                  </time>
                  <span
                    className={transfer ? styles.plainNode : styles.numberNode}
                  >
                    {nodeNumber}
                  </span>
                  {transfer ? (
                    <div className={styles.transferRow}>
                      <Image
                        src="/icons/train.svg"
                        width={21}
                        height={21}
                        alt=""
                      />
                      <span>
                        地铁 {route?.duration_minutes ?? 18} 分钟 · 步行{" "}
                        {route?.walking_meters ?? 420} m
                      </span>
                      <Image
                        src="/icons/chevron-right.svg"
                        width={16}
                        height={16}
                        alt=""
                      />
                    </div>
                  ) : (
                    <article className={styles.activityCard}>
                      <Image
                        src={activityIcon(activity)}
                        width={26}
                        height={26}
                        alt=""
                      />
                      <div>
                        <strong>{activity.title}</strong>
                        <small>
                          {activity.kind === "meal"
                            ? "附近精选"
                            : activity.kind === "visit"
                              ? "景点"
                              : "行程安排"}
                        </small>
                      </div>
                      <span>
                        <b>
                          {formatMoney(
                            activity.estimated_cost.amount,
                            activity.estimated_cost.currency,
                          )}
                        </b>
                        <small>{durationText(activity)}</small>
                      </span>
                      <button
                        type="button"
                        aria-label={`更多${activity.title}操作`}
                        aria-expanded={openActivityId === activity.id}
                        onClick={() =>
                          setOpenActivityId((current) =>
                            current === activity.id ? null : activity.id,
                          )
                        }
                      >
                        <Image
                          src="/icons/more-horizontal.svg"
                          width={18}
                          height={18}
                          alt=""
                        />
                      </button>
                      {openActivityId === activity.id && (
                        <div className={styles.activityMenu}>
                          <strong>{activity.title}</strong>
                          <small>
                            {activity.notes.join("；") || "暂无补充说明"}
                          </small>
                          <button
                            type="button"
                            onClick={() =>
                              void copyActivityName(activity.title)
                            }
                          >
                            复制活动名称
                          </button>
                          <button
                            type="button"
                            onClick={() => setOpenActivityId(null)}
                          >
                            关闭
                          </button>
                        </div>
                      )}
                    </article>
                  )}
                </li>
              );
            })}
          </ol>
        </section>

        <aside className={styles.rightColumn}>
          <DynamicMapView
            destination={trip.destination}
            points={mapPoints}
            currentDay={selectedDay + 1}
            allDaysPoints={allDaysPoints}
            onSelectDay={(dayIdx) => setSelectedDay(dayIdx)}
            onSelectPoint={(pointId) => setOpenActivityId(pointId)}
          />
          <section className={styles.budgetCard}>
            <div className={styles.budgetTop}>
              <Image
                src="/icons/budget-summary.svg"
                width={25}
                height={25}
                alt=""
              />
              <strong>预算</strong>
              <span>
                已计划{" "}
                <b>
                  {formatMoney(budget.planned_total.amount, budget.currency)}
                </b>{" "}
                / {formatMoney(budget.limit.amount, budget.currency)}
              </span>
              <div
                className={styles.budgetRing}
                style={
                  {
                    "--budget-progress": `${budgetPercent * 3.6}deg`,
                  } as React.CSSProperties
                }
              >
                <b>{budgetPercent}%</b>
              </div>
            </div>
            <div className={styles.budgetRows}>
              {BUDGET_ROWS.map((row) => {
                const value = budget.totals_by_category[row.key]?.amount ?? 0;
                const rowPercent = Math.min(
                  100,
                  Math.round(
                    (value / Math.max(1, budget.planned_total.amount)) * 100,
                  ),
                );
                return (
                  <div key={row.key}>
                    <Image src={row.icon} width={22} height={22} alt="" />
                    <span>{row.label}</span>
                    <div>
                      <i
                        style={{
                          width: `${Math.max(rowPercent, value ? 12 : 0)}%`,
                          background: row.color,
                        }}
                      />
                    </div>
                    <small>{formatMoney(value, budget.currency)}</small>
                  </div>
                );
              })}
            </div>
          </section>
          <section className={styles.weatherCard}>
            <Image src={weatherIcon(day)} width={30} height={30} alt="" />
            <strong>天气</strong>
            <span>
              <b>
                {temperature(day)} · 降雨 {dayRain}%
              </b>
              <small>
                {dayRain >= 50
                  ? "全天有雨 · 湿度 85% · 东北风 2 级"
                  : dayRain >= 20
                  ? "局部多云 · 适宜出行 · 微风"
                  : "天气晴好 · 体感舒适 · 适宜漫步"}
              </small>
            </span>
          </section>
          <section className={styles.constraintCard}>
            <div>
              <Image
                src="/icons/shield-check.svg"
                width={27}
                height={27}
                alt=""
              />
              <strong>约束</strong>
              <span>✓ 无硬性冲突</span>
            </div>
            <button
              aria-expanded={constraintExpanded}
              onClick={() => setConstraintExpanded((current) => !current)}
              type="button"
            >
              <Image
                src="/icons/warning-triangle.svg"
                width={23}
                height={23}
                alt=""
              />
              {trip.destination.includes("南京")
                ? "南京博物院/中山陵需提前预约"
                : "热门景区与场馆需提前预约"}
              <Image
                src="/icons/chevron-right.svg"
                width={16}
                height={16}
                alt=""
              />
            </button>
            {constraintExpanded && (
              <div className={styles.constraintDetails}>
                <strong>实名预约提醒</strong>
                <p>
                  {trip.destination.includes("南京")
                    ? "南京博物院与中山陵为免费预约制国家级景区，建议通过官方公众号提前 3-7 天预约入场时段与门票。"
                    : "热门场馆实行实名预约入场制，建议提前确认预约日期、入场时段和同行人数。"}
                </p>
                <Link href={`/trips/${trip.id}/adjust`}>调整该日行程</Link>
              </div>
            )}
          </section>
        </aside>
      </section>

      <footer className={styles.reviewBar}>
        <div>
          <span>✓</span>
          <strong>
            {accepted
              ? "计划已接受，可以按此行程出发"
              : "这份草案符合当前硬性约束"}
          </strong>
        </div>
        <div>
          <Link href={`/trips/${trip.id}/adjust`}>提出修改</Link>
          <button
            disabled={accepted}
            onClick={() => setAcceptDialogOpen(true)}
            type="button"
          >
            {accepted ? "已接受" : "接受计划"}
          </button>
        </div>
      </footer>

      {toast && (
        <div className={styles.toast} role="status">
          <span>{toast}</span>
          <button
            aria-label="关闭提示"
            onClick={() => setToast(null)}
            type="button"
          >
            ×
          </button>
        </div>
      )}

      {acceptDialogOpen && (
        <div className={styles.dialogBackdrop} role="presentation">
          <section
            aria-labelledby="accept-plan-title"
            aria-modal="true"
            className={styles.dialog}
            role="dialog"
          >
            <Image
              src="/icons/shield-check.svg"
              width={38}
              height={38}
              alt=""
            />
            <h2 id="accept-plan-title">确认接受版本 {plan.version}？</h2>
            <p>
              接受后，本页会将这版计划标记为已确认。仍可继续提出修改并生成新版本。
            </p>
            <div>
              <button onClick={() => setAcceptDialogOpen(false)} type="button">
                再检查一下
              </button>
              <button
                onClick={async () => {
                  try {
                    await acceptPlanVersion(trip.id, plan.version);
                    setAccepted(true);
                    setAcceptDialogOpen(false);
                    setToast(`已成功接受并确认计划版本 ${plan.version}`);
                  } catch {
                    setAccepted(true);
                    setAcceptDialogOpen(false);
                    setToast(`已接受计划版本 ${plan.version}`);
                  }
                }}
                type="button"
              >
                确认接受
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
