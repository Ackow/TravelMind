"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { listTrips, type TripResponse } from "@/lib/api/trips";
import styles from "./history-plans-list.module.css";

interface TripSummaryItem {
  id: string;
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
  dayCount: number;
  travelers: number;
  budgetAmount: number;
  currency: string;
  status: "confirmed" | "planning" | "draft";
  version: number;
  tags: string[];
  updatedAt: string;
}

function countDays(startDate?: string, endDate?: string): number {
  if (!startDate || !endDate) return 5;
  try {
    const start = new Date(startDate).getTime();
    const end = new Date(endDate).getTime();
    const diff = Math.round((end - start) / (1000 * 60 * 60 * 24)) + 1;
    return diff > 0 ? diff : 5;
  } catch {
    return 5;
  }
}

function formatRelativeTime(isoString?: string): string {
  if (!isoString) return "刚刚";
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return "刚刚";
  }
}

function formatMoney(cents: number, currency = "CNY") {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function mapTripToSummary(trip: TripResponse): TripSummaryItem {
  const isConfirmed =
    trip.status === "completed" ||
    (trip.current_plan_version !== null && trip.current_plan_version >= 1);

  return {
    id: trip.id,
    origin: trip.origin,
    destination: trip.destination,
    startDate: trip.date_range.start_date,
    endDate: trip.date_range.end_date,
    dayCount: countDays(trip.date_range.start_date, trip.date_range.end_date),
    travelers: trip.travelers,
    budgetAmount: trip.constraints.total_budget.amount,
    currency: trip.constraints.total_budget.currency || "CNY",
    status: isConfirmed ? "confirmed" : trip.status === "planning" ? "planning" : "draft",
    version: trip.current_plan_version || 1,
    tags: trip.preferences.interests.map((i) => i.value),
    updatedAt: formatRelativeTime(trip.updated_at),
  };
}

export function HistoryPlansList() {
  const [plans, setPlans] = useState<TripSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const dbTrips = await listTrips(50);
        if (isMounted && Array.isArray(dbTrips) && dbTrips.length > 0) {
          setPlans(dbTrips.map(mapTripToSummary));
          setLoading(false);
          return;
        }
      } catch (err) {
        console.warn("Failed to fetch trips from database API, checking fallback:", err);
      }

      // 降级：从本地缓存读取真实创建过的记录
      try {
        const stored = window.localStorage.getItem("travelmind-recent-trips");
        if (stored && isMounted) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setPlans(
              parsed
                .filter((item: any) => item && item.id && item.destination)
                .map((item: any) => ({
                  id: item.id,
                  origin: item.origin || "出发地",
                  destination: item.destination,
                  startDate: item.date_range?.start_date || "",
                  endDate: item.date_range?.end_date || "",
                  dayCount: countDays(item.date_range?.start_date, item.date_range?.end_date),
                  travelers: item.travelers || 1,
                  budgetAmount: item.constraints?.total_budget?.amount || 0,
                  currency: item.constraints?.total_budget?.currency || "CNY",
                  status: item.current_plan_version ? "confirmed" : "draft",
                  version: item.current_plan_version || 1,
                  tags: item.preferences?.interests?.map((i: any) => i.value) || [],
                  updatedAt: "刚刚",
                }))
            );
          }
        }
      } catch {
        // ignore
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const totalCount = plans.length;
  const confirmedCount = plans.filter((p) => p.status === "confirmed").length;
  const citiesCount = new Set(plans.map((p) => p.destination)).size;

  return (
    <main className={styles.page}>
      <header className={styles.headerSection}>
        <div>
          <p className={styles.eyebrow}>计划档案库</p>
          <h1 className={styles.title}>历史旅行计划</h1>
          <p className={styles.subtitle}>
            查看与管理所有生成的行程计划、版本演进对比与详细路书。
          </p>
        </div>
        <Link className={styles.createBtn} href="/trips/new">
          <span>＋</span> 创建新计划
        </Link>
      </header>

      {/* 统计指标栏 */}
      <section className={styles.statsBar} aria-label="计划统计数据">
        <div className={styles.statItem}>
          <label>已归档计划</label>
          <strong>{totalCount} 个</strong>
        </div>
        <div className={styles.statItem}>
          <label>已确认出案</label>
          <strong>{confirmedCount} 份</strong>
        </div>
        <div className={styles.statItem}>
          <label>探索城市</label>
          <strong>{citiesCount} 座</strong>
        </div>
      </section>

      {/* 历史计划卡片列表 */}
      {loading ? (
        <div className={styles.emptyState}>
          <p>正在从数据库加载历史计划...</p>
        </div>
      ) : plans.length === 0 ? (
        <section className={styles.emptyState}>
          <Image src="/icons/calendar.svg" width={48} height={48} alt="" />
          <h3>暂无历史旅行计划</h3>
          <p>开始创建你的第一份智能动态旅行规划吧。</p>
          <Link className={styles.createBtn} href="/trips/new">
            立即创建
          </Link>
        </section>
      ) : (
        <section className={styles.plansGrid} aria-label="旅行计划列表">
          {plans.map((plan) => {
            const isConfirmed = plan.status === "confirmed";
            const detailUrl = isConfirmed
              ? `/trips/${plan.id}/final`
              : `/trips/${plan.id}`;
            const historyUrl = `/trips/${plan.id}/history`;

            return (
              <article key={plan.id} className={styles.planCard}>
                <div className={styles.cardTop}>
                  <h2 className={styles.routeTitle}>
                    <span>{plan.origin}</span>
                    <span className={styles.routeArrow}>→</span>
                    <span>{plan.destination}</span>
                  </h2>
                  <div className={styles.badgeGroup}>
                    <span
                      className={`${styles.statusBadge} ${
                        isConfirmed ? styles.statusConfirmed : styles.statusDraft
                      }`}
                    >
                      {isConfirmed ? "✓ 已确认" : "⏳ 草案中"}
                    </span>
                    <span className={styles.versionBadge}>版本 {plan.version}</span>
                  </div>
                </div>

                <div className={styles.cardMetaGrid}>
                  <div className={styles.metaCol}>
                    <Image src="/icons/calendar.svg" width={18} height={18} alt="" />
                    <span>
                      {plan.startDate} ~ {plan.endDate} ({plan.dayCount}天{plan.dayCount - 1}晚)
                    </span>
                  </div>
                  <div className={styles.metaCol}>
                    <Image src="/icons/user.svg" width={18} height={18} alt="" />
                    <span>{plan.travelers} 位旅行者</span>
                  </div>
                  <div className={styles.metaCol}>
                    <Image src="/icons/wallet.svg" width={18} height={18} alt="" />
                    <span>总预算 {formatMoney(plan.budgetAmount, plan.currency)}</span>
                  </div>
                </div>

                {plan.tags.length > 0 && (
                  <div className={styles.tagsRow}>
                    <span className={styles.tagLabel}>偏好主题:</span>
                    {plan.tags.map((tag) => (
                      <span key={tag} className={styles.tagChip}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className={styles.cardActions}>
                  <Link className={styles.secondaryLink} href={historyUrl}>
                    版本演进历史 →
                  </Link>
                  <Link className={styles.primaryLink} href={detailUrl}>
                    查看行程详情
                  </Link>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
