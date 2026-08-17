"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  getCurrentPlan,
  type PlanActivity,
  type PlanDay,
  type PlanVersionResponse,
  type TripResponse,
} from "@/lib/api/trips";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
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
          setSelectedDay(result.itinerary.days.length > 1 ? 1 : 0);
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
          <div className={styles.mapCard} aria-label="东京路线示意图">
            <div className={styles.mapGrid} />
            <div className={styles.routeLine} />
            <span className={styles.mapName1}>上野</span>
            <span className={styles.mapName2}>秋叶原</span>
            <span className={styles.mapName3}>东京站</span>
            {[1, 2, 3, 4].map((number) => (
              <i className={styles[`pin${number}`]} key={number}>
                {number}
              </i>
            ))}
          </div>
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
              <small>全天有雨 · 湿度 85% · 东北风 2 级</small>
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
              teamLab 需提前预约{" "}
              <Image
                src="/icons/chevron-right.svg"
                width={16}
                height={16}
                alt=""
              />
            </button>
            {constraintExpanded && (
              <div className={styles.constraintDetails}>
                <strong>预约提示</strong>
                <p>
                  该项目需要提前预约。建议出发前确认预约日期、入场时段和同行人数。
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
                onClick={() => {
                  setAccepted(true);
                  setAcceptDialogOpen(false);
                  setToast(`已接受计划版本 ${plan.version}`);
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
