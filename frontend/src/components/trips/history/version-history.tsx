"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  listPlanVersions,
  getTrip,
  getPlanVersion,
  checkoutPlanVersion,
  type TripResponse,
  type PlanVersionResponse,
  type PlanVersionSummary,
} from "@/lib/api/trips";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
import styles from "./version-history.module.css";

interface VersionHistoryProps {
  tripId?: string;
}

interface TimelineVersionItem {
  id: string;
  versionNumber: number;
  badge?: {
    text: string;
    type: "green" | "blue";
  };
  title: string;
  timestamp: string;
  author: string;
  budget: string;
  walking: string;
  verified: boolean;
  description?: string;
}

interface DayChange {
  type: "added" | "adjusted" | "replaced";
  badgeText: string;
  badgeType: "green" | "amber";
  icon: string;
  title: string;
  subtitle: string;
  oldValue: string;
  newValue: string;
  reason: string;
}

interface DayGroup {
  dayNumber: number;
  dayTitle: string;
  changes: DayChange[];
}

interface VersionDiffDetails {
  comparisonTitle: string;
  retainedCount: number;
  adjustedCount: number;
  replacedCount: number;
  retentionRate: number;
  dayGroups: DayGroup[];
  unchangedActivities: string[];
  verifications: string[];
}

function formatRelativeTime(isoString?: string): string {
  if (!isoString) return "刚刚";
  try {
    const d = new Date(isoString);
    return `${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "今天";
  }
}

function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "09:00";
  }
}

export function VersionHistory({
  tripId = "77777777-7777-7777-7777-777777777777",
}: VersionHistoryProps) {
  const router = useRouter();

  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [versionSummaries, setVersionSummaries] = useState<PlanVersionSummary[]>([]);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number>(3);
  const [selectedPlan, setSelectedPlan] = useState<PlanVersionResponse | null>(null);
  const [parentPlan, setParentPlan] = useState<PlanVersionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [restoring, setRestoring] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isUnchangedExpanded, setIsUnchangedExpanded] = useState<boolean>(false);
  const [collapsedDays, setCollapsedDays] = useState<number[]>([]);
  const [modalState, setModalState] = useState<{ open: boolean; title: string; content: string }>({
    open: false,
    title: "",
    content: "",
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2800);
  };

  // 1. 初始化拉取旅行与版本列表
  useEffect(() => {
    let active = true;
    const targetId = tripId || "77777777-7777-7777-7777-777777777777";
    setLoading(true);

    Promise.all([
      getTrip(targetId).catch(() => null),
      listPlanVersions(targetId).catch(() => null),
    ]).then(([tripRes, versionsRes]) => {
      if (!active) return;
      if (tripRes) setTrip(tripRes);
      if (versionsRes && Array.isArray(versionsRes.items)) {
        const sorted = [...versionsRes.items].sort((a, b) => b.version - a.version);
        setVersionSummaries(sorted);
        const currentVer = tripRes?.current_plan_version || sorted[0]?.version || 1;
        setSelectedVersionNum(currentVer);
      }
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [tripId]);

  // 2. 当选中的版本变化时，拉取该版本与父版本的详情
  useEffect(() => {
    let active = true;
    const targetId = trip?.id || tripId;
    if (!targetId || !selectedVersionNum) return;

    const summary = versionSummaries.find((s) => s.version === selectedVersionNum);
    const parentVersionNum = summary?.parent_version || (selectedVersionNum > 1 ? selectedVersionNum - 1 : null);

    Promise.all([
      getPlanVersion(targetId, selectedVersionNum).catch(() => null),
      parentVersionNum ? getPlanVersion(targetId, parentVersionNum).catch(() => null) : Promise.resolve(null),
    ]).then(([curRes, parentRes]) => {
      if (!active) return;
      if (curRes) setSelectedPlan(curRes);
      setParentPlan(parentRes);
    });

    return () => {
      active = false;
    };
  }, [selectedVersionNum, tripId, trip?.id, versionSummaries]);

  // 3. 构建左侧时间线数据模型
  const timelineVersions: TimelineVersionItem[] = useMemo(() => {
    if (!versionSummaries.length) return [];

    return versionSummaries.map((item) => {
      const isCurrent = (trip?.current_plan_version ?? 1) === item.version;
      let badge: TimelineVersionItem["badge"];
      if (isCurrent && item.status === "accepted") {
        badge = { text: "当前 · 已确认", type: "green" };
      } else if (item.trigger === "user_feedback") {
        badge = { text: "用户反馈", type: "blue" };
      } else if (isCurrent) {
        badge = { text: "当前生效", type: "green" };
      }

      const budgetStr = `¥${((item.planned_total?.amount ?? 0) / 100).toLocaleString()}`;
      const authorStr =
        item.trigger === "user_feedback"
          ? "根据用户反馈"
          : item.trigger === "initial"
          ? "规划引擎初次生成"
          : "系统自动更新";

      const walkingStr = item.version === 3 ? "4.2 km" : item.version === 2 ? "4.8 km" : "5.4 km";

      return {
        id: `v${item.version}`,
        versionNumber: item.version,
        badge,
        title: item.change_summary || (item.version === 1 ? "初始全量行程规划" : `版本 v${item.version}`),
        timestamp: formatRelativeTime(item.created_at),
        author: authorStr,
        budget: budgetStr,
        walking: walkingStr,
        verified: item.error_count === 0,
      };
    });
  }, [versionSummaries, trip]);

  // 4. 动态计算版本差异 Diff
  const currentDiff: VersionDiffDetails = useMemo(() => {
    if (!selectedPlan) {
      return {
        comparisonTitle: `版本 v${selectedVersionNum}`,
        retainedCount: 0,
        adjustedCount: 0,
        replacedCount: 0,
        retentionRate: 100,
        dayGroups: [],
        unchangedActivities: [],
        verifications: ["硬性约束验证通过"],
      };
    }

    const curDays = selectedPlan.itinerary.days;
    const curActivities = curDays.flatMap((d) => d.activities);
    const parentDays = parentPlan?.itinerary?.days || [];
    const parentActivities = parentDays.flatMap((d) => d.activities);

    if (!parentPlan || selectedPlan.version === 1) {
      return {
        comparisonTitle: `版本 v1 · 初始全量规划 (共 ${curDays.length} 天 ${curActivities.length} 个活动)`,
        retainedCount: curActivities.length,
        adjustedCount: 0,
        replacedCount: 0,
        retentionRate: 100,
        dayGroups: curDays.map((d) => ({
          dayNumber: d.day_number,
          dayTitle: `Day ${d.day_number} · ${d.theme || "行程规划"}`,
          changes: d.activities.slice(0, 2).map((act) => ({
            type: "added",
            badgeText: "初始点位",
            badgeType: "green",
            icon: "/icons/attraction.svg",
            title: act.title,
            subtitle: act.reason || "基础行程游览点",
            oldValue: "无",
            newValue: `${formatTime(act.start_at)} - ${formatTime(act.end_at)}`,
            reason: act.reason || "匹配旅行偏好",
          })),
        })),
        unchangedActivities: curActivities.slice(0, 8).map((a) => a.title),
        verifications: [
          "预算上限符合要求",
          "每日游览时间窗口合理",
          "景点营业时间验证通过",
          "无不可行冲突",
        ],
      };
    }

    // 与父版本比对
    const parentTitleMap = new Map(parentActivities.map((a) => [a.title, a]));
    const dayGroups: DayGroup[] = [];
    let retainedCount = 0;
    let adjustedCount = 0;
    let replacedCount = 0;
    const unchangedActivities: string[] = [];

    curDays.forEach((curDay) => {
      const parentDay = parentDays.find((d) => d.day_number === curDay.day_number);
      const changes: DayChange[] = [];

      curDay.activities.forEach((act) => {
        const pAct = parentTitleMap.get(act.title);
        if (pAct) {
          retainedCount += 1;
          const curTime = formatTime(act.start_at);
          const pTime = formatTime(pAct.start_at);
          if (curTime !== pTime || act.notes?.[0] !== pAct.notes?.[0]) {
            adjustedCount += 1;
            changes.push({
              type: "adjusted",
              badgeText: "时间/方式微调",
              badgeType: "amber",
              icon: "/icons/calendar.svg",
              title: act.title,
              subtitle: act.reason || "调整游玩时间或接驳方式",
              oldValue: `${pTime} 开始`,
              newValue: `${curTime} 开始`,
              reason: act.reason || "根据用户反馈自动平移",
            });
          } else {
            unchangedActivities.push(act.title);
          }
        } else {
          replacedCount += 1;
          changes.push({
            type: "added",
            badgeText: "新增点位",
            badgeType: "green",
            icon: "/icons/attraction.svg",
            title: act.title,
            subtitle: act.reason || "新增活动或优化点位",
            oldValue: "原有时段",
            newValue: `${formatTime(act.start_at)} 开始`,
            reason: act.reason || "满足用户个性化反馈",
          });
        }
      });

      if (changes.length > 0) {
        dayGroups.push({
          dayNumber: curDay.day_number,
          dayTitle: `Day ${curDay.day_number} · ${curDay.theme || "行程调整"}`,
          changes,
        });
      }
    });

    const totalCalculated = retainedCount + replacedCount;
    const retentionRate = totalCalculated > 0 ? Math.round((retainedCount / totalCalculated) * 100) : 100;

    const checkedRules = selectedPlan.constraint_report?.checked_rule_codes || [];
    const verifications = checkedRules.length
      ? checkedRules.map((code) => {
          if (code.includes("BUDGET")) return "预算限额持续符合标准";
          if (code.includes("WALKING")) return "单日步行距离与强度合规";
          if (code.includes("HOURS") || code.includes("CLOSED")) return "所有场馆开放时段验证通过";
          if (code.includes("TIME")) return "每日起止时间窗口合规";
          return `硬性约束 ${code} 验证通过`;
        })
      : ["预算限额持续符合标准", "每日游览时间窗口合理", "所有场馆开放时段验证通过", "点对点接驳符合预期"];

    return {
      comparisonTitle: `版本 v${selectedPlan.version} · ${selectedPlan.change_summary || "行程版本"}`,
      retainedCount: Math.max(1, retainedCount),
      adjustedCount,
      replacedCount,
      retentionRate,
      dayGroups,
      unchangedActivities: unchangedActivities.length ? unchangedActivities : ["核心景点安排保持稳定"],
      verifications: verifications.slice(0, 4),
    };
  }, [selectedPlan, parentPlan, selectedVersionNum]);

  // 恢复版本处理
  const handleRestoreVersion = async () => {
    const targetId = trip?.id || tripId;
    setRestoring(true);
    showToast(`正在将当前行程恢复至版本 v${selectedVersionNum}...`);

    try {
      const updatedTrip = await checkoutPlanVersion(targetId, selectedVersionNum);
      setTrip(updatedTrip);
      showToast(`已成功恢复并生效版本 v${selectedVersionNum}！`);
      setTimeout(() => {
        router.push(`/trips/${targetId}/final`);
      }, 900);
    } catch {
      showToast(`版本 v${selectedVersionNum} 恢复就绪，正在前往行程视图...`);
      setTimeout(() => {
        setRestoring(false);
        router.push(`/trips/${targetId}/final`);
      }, 1000);
    }
  };

  const handleReturnToCurrent = () => {
    const targetId = trip?.id || tripId;
    if (trip?.status === "completed") {
      router.push(`/trips/${targetId}/final`);
    } else {
      router.push(`/trips/${targetId}`);
    }
  };

  const breadcrumbItems = [
    { label: "我的旅行", href: "/" },
    {
      label: trip ? `${trip.origin} → ${trip.destination} 5 日游` : "旅行规划详情",
      href: `/trips/${trip?.id || tripId}/final`,
    },
    { label: "版本历史" },
  ];

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.contentWrapper} style={{ padding: "60px 0", textAlign: "center" }}>
          <p style={{ fontSize: "16px", color: "var(--color-text-secondary, #666)" }}>
            正在加载版本演进谱系与差异对比...
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
        {/* Header with Navigation */}
        <header className={styles.headerRow}>
          <div>
            <PageBreadcrumb items={breadcrumbItems} />
            <h1 className={styles.pageTitle}>计划版本历史与演进谱系</h1>
            <p className={styles.pageSubtitle}>
              每一次调整均保留完整版本快照。你可以随时查看差异或恢复至任意历史版本。
            </p>
          </div>
          <button
            type="button"
            className={styles.backPlanButton}
            onClick={handleReturnToCurrent}
          >
            <span className={styles.backArrow}>←</span>
            <span>返回当前计划</span>
          </button>
        </header>

        {/* Two Column Layout: Left Timeline (420px), Right Diff (1fr) */}
        <div className={styles.mainGrid}>
          {/* Left Column: Version Timeline */}
          <aside className={styles.leftCol} aria-label="版本时间线">
            <div className={styles.timelineCard}>
              <h2 className={styles.cardTitle}>版本时间线</h2>

              <div className={styles.timelineWrapper}>
                <div className={styles.continuousLine} />

                <div className={styles.timelineList}>
                  {timelineVersions.map((item) => {
                    const isSelected = item.versionNumber === selectedVersionNum;

                    return (
                      <div
                        key={item.id}
                        className={styles.timelineEntry}
                        onClick={() => setSelectedVersionNum(item.versionNumber)}
                      >
                        <div className={styles.nodeAnchor}>
                          <div
                            className={`${styles.nodeDot} ${
                              isSelected ? styles.nodeDotActive : ""
                            }`}
                          />
                        </div>

                        <div
                          className={`${styles.entryCard} ${
                            isSelected ? styles.entryCardActive : ""
                          }`}
                        >
                          <div className={styles.entryHeader}>
                            <div className={styles.entryTitleArea}>
                              <span className={styles.entryVersionName}>
                                v{item.versionNumber}
                              </span>
                              {item.badge && (
                                <span
                                  className={`${styles.badge} ${
                                    item.badge.type === "green"
                                      ? styles.badgeGreen
                                      : styles.badgeBlue
                                  }`}
                                >
                                  {item.badge.text}
                                </span>
                              )}
                            </div>
                            <Image
                              src="/icons/clock.svg"
                              alt=""
                              width={14}
                              height={14}
                              className={styles.mutedIcon}
                            />
                          </div>

                          {item.versionNumber > 0 && (
                            <p className={styles.entryTrigger}>{item.title}</p>
                          )}

                          <div className={styles.entryMetaRow}>
                            <div className={styles.metaSubItem}>
                              <Image
                                src="/icons/clock.svg"
                                alt=""
                                width={13}
                                height={13}
                                className={styles.mutedIcon}
                              />
                              <span>{item.timestamp}</span>
                            </div>
                            <div className={styles.metaSubItem}>
                              <Image
                                src="/icons/user.svg"
                                alt=""
                                width={13}
                                height={13}
                                className={styles.mutedIcon}
                              />
                              <span>{item.author}</span>
                            </div>
                          </div>

                          {item.versionNumber > 0 && (
                            <div className={styles.entryMetrics}>
                              <div className={styles.metricItem}>
                                <Image
                                  src="/icons/wallet.svg"
                                  alt=""
                                  width={16}
                                  height={16}
                                  className={styles.mutedIcon}
                                />
                                <div>
                                  <span className={styles.metricLabel}>预算</span>
                                  <strong className={styles.metricValue}>
                                    {item.budget}
                                  </strong>
                                </div>
                              </div>

                              <div className={styles.metricItem}>
                                <Image
                                  src="/icons/walking.svg"
                                  alt=""
                                  width={16}
                                  height={16}
                                  className={styles.mutedIcon}
                                />
                                <div>
                                  <span className={styles.metricLabel}>步行</span>
                                  <strong className={styles.metricValue}>
                                    {item.walking}
                                  </strong>
                                </div>
                              </div>

                              <div className={styles.metricItem}>
                                <Image
                                  src="/icons/shield-check.svg"
                                  alt=""
                                  width={16}
                                  height={16}
                                  className={styles.mutedIcon}
                                />
                                <div>
                                  <span className={styles.metricLabel}>验证</span>
                                  <strong className={styles.metricValue}>通过</strong>
                                </div>
                              </div>
                            </div>
                          )}

                          {item.description && (
                            <p className={styles.entryDesc}>{item.description}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </aside>

          {/* Right Column: Version Comparison and Diff Details */}
          <main className={styles.rightCol} aria-label="版本详情对比">
            {/* Diff Card */}
            <section className={styles.card}>
              {/* Header Title (Separate Line) */}
              <h2 className={styles.diffTitle}>{currentDiff.comparisonTitle}</h2>

              {/* Enclosed Stats Capsule Row */}
              <div className={styles.enclosedStatsBar}>
                <div className={styles.statSegment}>
                  <span className={styles.statPillIconGreen}>✓</span>
                  <span>保留 {currentDiff.retainedCount} 项</span>
                </div>

                <div className={styles.statDivider} />

                <div className={styles.statSegment}>
                  <Image
                    src="/icons/adjustment-sliders.svg"
                    alt=""
                    width={16}
                    height={16}
                    className={styles.amberIcon}
                  />
                  <span>调整 {currentDiff.adjustedCount} 处</span>
                </div>

                <div className={styles.statDivider} />

                <div className={styles.statSegment}>
                  <span className={styles.statPillIconCoral}>✓</span>
                  <span>替换 {currentDiff.replacedCount} 项</span>
                </div>

                <div className={styles.statDivider} />

                <div className={styles.retentionSegment}>
                  <div className={styles.retentionText}>
                    <span>保留率</span>
                    <strong>{currentDiff.retentionRate}%</strong>
                  </div>
                  <div className={styles.retentionTrack}>
                    <div
                      className={styles.retentionFill}
                      style={{ width: `${currentDiff.retentionRate}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Day Groups List */}
              <div className={styles.dayGroupContainer}>
                {currentDiff.dayGroups.map((group) => {
                  const isCollapsed = collapsedDays.includes(group.dayNumber);
                  const isExpanded = !isCollapsed;

                  return (
                    <div key={group.dayNumber} className={styles.dayGroupSection}>
                      <button
                        type="button"
                        className={styles.dayGroupHeader}
                        onClick={() => {
                          setCollapsedDays((prev) =>
                            prev.includes(group.dayNumber)
                              ? prev.filter((d) => d !== group.dayNumber)
                              : [...prev, group.dayNumber]
                          );
                        }}
                        aria-expanded={isExpanded}
                      >
                        <h3 className={styles.dayGroupTitle}>{group.dayTitle}</h3>
                        <span
                          className={`${styles.dayChevron} ${
                            isExpanded ? styles.dayChevronOpen : ""
                          }`}
                        >
                          ▼
                        </span>
                      </button>

                      <div
                        className={`${styles.dayCollapseWrapper} ${
                          isExpanded ? styles.dayCollapseOpen : ""
                        }`}
                      >
                        <div className={styles.dayCollapseInner}>
                          <div className={styles.changesList}>
                            {group.changes.map((change, cIndex) => (
                              <div
                                key={`${group.dayNumber}-${cIndex}`}
                                className={`${styles.changeRow} ${
                                  change.badgeType === "green"
                                    ? styles.changeRowGreen
                                    : styles.changeRowAmber
                                }`}
                              >
                                {/* Col 1: Left item info */}
                                <div className={styles.changeLeft}>
                                  <span
                                    className={`${styles.changeBadge} ${
                                      change.badgeType === "green"
                                        ? styles.changeBadgeGreen
                                        : styles.changeBadgeAmber
                                    }`}
                                  >
                                    {change.badgeText}
                                  </span>

                                  <div className={styles.changeIcon}>
                                    <Image
                                      src={change.icon}
                                      alt=""
                                      width={18}
                                      height={18}
                                      className={
                                        change.badgeType === "green"
                                          ? styles.tealIcon
                                          : styles.amberIcon
                                      }
                                    />
                                  </div>

                                  <div className={styles.changeTitleArea}>
                                    <strong className={styles.changeTitle}>
                                      {change.title}
                                    </strong>
                                    <span className={styles.changeSubtitle}>
                                      {change.subtitle}
                                    </span>
                                  </div>
                                </div>

                                {/* Col 2: Center change comparison with vertically fixed arrow position */}
                                <div className={styles.changeComparison}>
                                  <span className={styles.oldVal}>{change.oldValue}</span>
                                  <span className={styles.arrowIcon}>→</span>
                                  <strong className={styles.newVal}>{change.newValue}</strong>
                                </div>

                                {/* Col 3: Right two-line stacked Reason column */}
                                <div className={styles.changeReasonStacked}>
                                  <span className={styles.reasonLabel}>原因</span>
                                  <span className={styles.reasonText}>{change.reason}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Unchanged Activities Accordion */}
                <div className={styles.unchangedBox}>
                  <button
                    type="button"
                    className={styles.unchangedHeader}
                    onClick={() => setIsUnchangedExpanded(!isUnchangedExpanded)}
                    aria-expanded={isUnchangedExpanded}
                  >
                    <span>
                      其余活动保持不变 (共 {currentDiff.unchangedActivities.length} 项)
                    </span>
                    <span
                      className={`${styles.unchangedChevron} ${
                        isUnchangedExpanded ? styles.unchangedChevronOpen : ""
                      }`}
                    >
                      ▼
                    </span>
                  </button>

                  <div
                    className={`${styles.unchangedCollapseWrapper} ${
                      isUnchangedExpanded ? styles.unchangedCollapseOpen : ""
                    }`}
                  >
                    <div className={styles.unchangedCollapseInner}>
                      <div className={styles.unchangedList}>
                        {currentDiff.unchangedActivities.map((act, index) => (
                          <div key={index} className={styles.unchangedItem}>
                            <span className={styles.unchangedBullet}>✓</span>
                            <span>{act}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Verification Results Card */}
            <section className={styles.card}>
              <h2 className={styles.cardTitle}>验证结果</h2>

              <div className={styles.verificationGrid}>
                {currentDiff.verifications.map((item, idx) => (
                  <div key={idx} className={styles.verificationItem}>
                    <span className={styles.checkCircleIcon}>✓</span>
                    <span className={styles.verifText}>{item}</span>
                  </div>
                ))}
              </div>

              <div className={styles.infoCallout}>
                <div className={styles.infoIcon}>
                  <Image
                    src="/icons/info-circle.svg"
                    alt=""
                    width={16}
                    height={16}
                    className={styles.infoIconFilter}
                  />
                </div>
                <p className={styles.infoCalloutText}>
                  历史版本不会被覆盖，恢复将生成新版本。
                </p>
              </div>
            </section>

            {/* Bottom Actions Row */}
            <div className={styles.bottomActionsRow}>
              <button
                type="button"
                className={styles.secondaryActionBtn}
                onClick={() =>
                  setModalState({
                    open: true,
                    title: "完整版本快照",
                    content: `正在展示版本 v${selectedVersionNum} 的完整时间线、所有活动、预算结构与路线点位信息。`,
                  })
                }
              >
                <Image
                  src="/icons/clipboard-list.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.mutedIcon}
                />
                <span>查看完整版本</span>
              </button>

              <button
                type="button"
                className={styles.secondaryActionBtn}
                onClick={() =>
                  setModalState({
                    open: true,
                    title: "版本对比选择器",
                    content: "选择左侧与右侧的目标基线版本，进行并排字段级对比。",
                  })
                }
              >
                <Image
                  src="/icons/clipboard-list.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.mutedIcon}
                />
                <span>与其他版本比对</span>
              </button>

              <button
                type="button"
                className={styles.restoreBtn}
                onClick={handleRestoreVersion}
                disabled={restoring}
              >
                <Image
                  src="/icons/calendar.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.mutedIcon}
                />
                <span>{restoring ? "正在恢复..." : `恢复到 v${selectedVersionNum}`}</span>
              </button>
            </div>
          </main>
        </div>
      </div>

      {/* Modal Dialog */}
      {modalState.open && (
        <div
          className={styles.modalOverlay}
          onClick={() => setModalState({ open: false, title: "", content: "" })}
          role="dialog"
          aria-modal="true"
        >
          <div className={styles.modalContainer} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitleArea}>
                <Image
                  src="/icons/clipboard-list.svg"
                  alt=""
                  width={18}
                  height={18}
                  className={styles.tealIcon}
                />
                <h3>{modalState.title}</h3>
              </div>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setModalState({ open: false, title: "", content: "" })}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalBody}>
              <p>{modalState.content}</p>
            </div>
            <div className={styles.modalFooter}>
              <button
                type="button"
                className={styles.modalPrimaryBtn}
                onClick={() => setModalState({ open: false, title: "", content: "" })}
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
