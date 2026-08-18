"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
import styles from "./version-history.module.css";

interface VersionHistoryProps {
  tripId?: string;
}

interface TimelineVersion {
  id: string;
  versionNumber: number;
  isCurrent?: boolean;
  badge?: {
    text: string;
    type: "green" | "blue";
  };
  title: string;
  timestamp: string;
  author: string;
  budget?: string;
  walking?: string;
  verified?: boolean;
  description?: string;
}

interface DayChange {
  type: "added" | "adjusted" | "replaced";
  badgeText: string;
  badgeType: "green" | "amber" | "coral";
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

const TIMELINE_DATA: TimelineVersion[] = [
  {
    id: "v3",
    versionNumber: 3,
    isCurrent: true,
    badge: { text: "当前 · 已确认", type: "green" },
    title: "减少每日步行距离",
    timestamp: "今天 14:32",
    author: "根据用户反馈",
    budget: "¥8,460",
    walking: "38.6 km",
    verified: true,
  },
  {
    id: "v2",
    versionNumber: 2,
    title: "Day 2 晚出发并保留日落",
    timestamp: "今天 13:06",
    author: "根据用户反馈",
    budget: "¥9,150",
    walking: "42.1 km",
    verified: true,
  },
  {
    id: "v1",
    versionNumber: 1,
    title: "初次规划",
    timestamp: "今天 11:48",
    author: "系统生成",
    budget: "¥9,850",
    walking: "48.3 km",
    verified: true,
  },
  {
    id: "v0-weather",
    versionNumber: 0,
    badge: { text: "系统更新", type: "blue" },
    title: "天气数据更新",
    timestamp: "今天 10:21",
    author: "自动刷新",
    description: "更新了 5 天的天气预报和降水概率数据",
  },
];

const DIFF_DATABASE: { [key: string]: VersionDiffDetails } = {
  v3: {
    comparisonTitle: "版本 3 相对版本 2",
    retainedCount: 15,
    adjustedCount: 2,
    replacedCount: 1,
    retentionRate: 88,
    dayGroups: [
      {
        dayNumber: 2,
        dayTitle: "Day 2 · 博物馆与东京站",
        changes: [
          {
            type: "added",
            badgeText: "+ 添加",
            badgeType: "green",
            icon: "/icons/attraction.svg",
            title: "江之岛海岸",
            subtitle: "海洋散步",
            oldValue: "—",
            newValue: "16:40 加入",
            reason: "保留日落活动",
          },
          {
            type: "adjusted",
            badgeText: "↓ 调整",
            badgeType: "amber",
            icon: "/icons/clock.svg",
            title: "上野午餐",
            subtitle: "用餐",
            oldValue: "12:30",
            newValue: "13:00",
            reason: "配合晚出发",
          },
        ],
      },
      {
        dayNumber: 4,
        dayTitle: "Day 4 · 镰仓一日",
        changes: [
          {
            type: "adjusted",
            badgeText: "↓ 调整",
            badgeType: "amber",
            icon: "/icons/train.svg",
            title: "镰仓交通方式",
            subtitle: "从镰仓站到长谷寺",
            oldValue: "步行 + 巴士",
            newValue: "电车优先",
            reason: "减少每日步行距离",
          },
        ],
      },
    ],
    unchangedActivities: [
      "Day 1 · 成田机场入境与取行李 (09:00 - 10:30)",
      "Day 1 · 入住浅草豪景酒店 (11:00 - 12:00)",
      "Day 1 · 浅草寺参拜与雷门 (14:00 - 15:30)",
      "Day 1 · 秋叶原电器街巡礼 (16:00 - 18:00)",
      "Day 1 · 晚餐鸟贵族 (19:00 - 20:00)",
      "Day 2 · 东京国立博物馆 (09:30 - 11:30)",
      "Day 2 · 上野公园散步 (14:30 - 16:00)",
      "Day 3 · 涩谷 Shibuya Sky (10:00 - 12:00)",
      "Day 3 · 表参道漫步与咖啡 (14:00 - 16:00)",
      "Day 4 · 镰仓大佛与高德院 (10:30 - 12:00)",
      "Day 5 · 银座购物与筑地外市 (10:00 - 13:00)",
      "Day 5 · 准备返程 (14:00 - 16:00)",
    ],
    verifications: [
      "预算仍在范围内",
      "开放时间可用",
      "换乘时间可行",
      "步行距离下降至 38.6 km",
    ],
  },
  v2: {
    comparisonTitle: "版本 2 相对版本 1",
    retainedCount: 14,
    adjustedCount: 3,
    replacedCount: 1,
    retentionRate: 78,
    dayGroups: [
      {
        dayNumber: 2,
        dayTitle: "Day 2 · 晚出发与日落调整",
        changes: [
          {
            type: "adjusted",
            badgeText: "↓ 调整",
            badgeType: "amber",
            icon: "/icons/clock.svg",
            title: "出发时间",
            subtitle: "酒店出发",
            oldValue: "09:00",
            newValue: "11:30",
            reason: "配合晚出发",
          },
          {
            type: "added",
            badgeText: "+ 添加",
            badgeType: "green",
            icon: "/icons/attraction.svg",
            title: "台场海滨公园",
            subtitle: "日落观景",
            oldValue: "—",
            newValue: "17:15 加入",
            reason: "保留日落活动",
          },
        ],
      },
    ],
    unchangedActivities: [
      "Day 1 · 全天常规行程保持不变",
      "Day 3 · 涩谷与表参道保持不变",
      "Day 4 · 镰仓全日游保持不变",
      "Day 5 · 银座返程保持不变",
    ],
    verifications: [
      "预算仍在范围内",
      "开放时间可用",
      "换乘时间可行",
      "步行距离 42.1 km",
    ],
  },
  v1: {
    comparisonTitle: "版本 1 (初始规划)",
    retainedCount: 18,
    adjustedCount: 0,
    replacedCount: 0,
    retentionRate: 100,
    dayGroups: [
      {
        dayNumber: 1,
        dayTitle: "初始全行程生成",
        changes: [
          {
            type: "added",
            badgeText: "+ 生成",
            badgeType: "green",
            icon: "/icons/clipboard-check.svg",
            title: "5 日行程全量生成",
            subtitle: "18 个精选活动与交通接驳",
            oldValue: "—",
            newValue: "全量规划通过",
            reason: "初始确定性约束规划",
          },
        ],
      },
    ],
    unchangedActivities: ["初始生成 18 个活动全部就绪"],
    verifications: [
      "预算仍在范围内",
      "开放时间可用",
      "换乘时间可行",
      "步行距离 48.3 km",
    ],
  },
  "v0-weather": {
    comparisonTitle: "天气数据更新",
    retainedCount: 18,
    adjustedCount: 0,
    replacedCount: 0,
    retentionRate: 100,
    dayGroups: [
      {
        dayNumber: 0,
        dayTitle: "外部环境数据同步",
        changes: [
          {
            type: "adjusted",
            badgeText: "⚡ 刷新",
            badgeType: "amber",
            icon: "/icons/capability-weather.svg",
            title: "东京 5 天气象预报",
            subtitle: "气温 17-26°C · 降雨概率",
            oldValue: "历史基线",
            newValue: "最新气象同步",
            reason: "自动定时刷新",
          },
        ],
      },
    ],
    unchangedActivities: ["天气变化未触发硬约束冲突，行程无需调整"],
    verifications: [
      "预算仍在范围内",
      "开放时间可用",
      "换乘时间可行",
      "步行距离 38.6 km",
    ],
  },
};

export function VersionHistory({ tripId = "tokyo-5d" }: VersionHistoryProps) {
  const router = useRouter();
  const [selectedVersionId, setSelectedVersionId] = useState<string>("v3");
  const [isUnchangedExpanded, setIsUnchangedExpanded] = useState<boolean>(false);
  const [modalState, setModalState] = useState<{
    open: boolean;
    title: string;
    content: string;
  } | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2600);
  };

  const breadcrumbItems = [
    { label: "我的旅行", href: "/" },
    { label: "东京 5 日游", href: `/trips/${tripId}` },
    { label: "版本历史" },
  ];

  const currentDiff = DIFF_DATABASE[selectedVersionId] || DIFF_DATABASE.v3;

  const handleRestoreVersion = (v: TimelineVersion) => {
    showToast(`正在基于“${v.title}”创建新版本...`);
    setTimeout(() => {
      showToast(`已成功恢复为版本 ${TIMELINE_DATA.length}（向前追加，历史不可变）`);
    }, 1200);
  };

  return (
    <div className={styles.pageContainer}>
      {/* Toast Alert */}
      {toastMessage && (
        <div className={styles.toast} role="alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{toastMessage}</span>
        </div>
      )}

      <div className={styles.contentWrapper}>
        {/* Header */}
        <header className={styles.headerRow}>
          <div>
            <PageBreadcrumb items={breadcrumbItems} />
            <h1 className={styles.pageTitle}>计划版本</h1>
            <p className={styles.pageSubtitle}>每次调整都会保存为一个不可变版本</p>
          </div>

          <button
            type="button"
            className={styles.backPlanButton}
            onClick={() => router.push(`/trips/${tripId}`)}
          >
            <span className={styles.backArrow}>←</span> 返回当前计划
          </button>
        </header>

        {/* Main 2-Column Layout */}
        <div className={styles.mainGrid}>
          {/* Left Column: Version Timeline */}
          <aside className={styles.leftCol} aria-label="版本时间线">
            <div className={styles.timelineCard}>
              <h2 className={styles.cardTitle}>版本时间线</h2>

              {/* Timeline Container with Continuous Background Line */}
              <div className={styles.timelineWrapper}>
                <div className={styles.continuousLine} />

                <div className={styles.timelineList}>
                  {TIMELINE_DATA.map((item) => {
                    const isSelected = selectedVersionId === item.id;

                    return (
                      <div
                        key={item.id}
                        className={`${styles.timelineEntry} ${
                          isSelected ? styles.timelineEntryActive : ""
                        }`}
                        onClick={() => setSelectedVersionId(item.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === " " || e.key === "Enter") setSelectedVersionId(item.id);
                        }}
                      >
                        {/* Node Dot positioned on continuous vertical line */}
                        <div className={styles.nodeAnchor}>
                          <div
                            className={`${styles.nodeDot} ${
                              isSelected ? styles.nodeDotActive : ""
                            }`}
                          />
                        </div>

                        {/* Content Box */}
                        <div
                          className={`${styles.entryCard} ${
                            isSelected ? styles.entryCardActive : ""
                          }`}
                        >
                          <div className={styles.entryHeader}>
                            <div className={styles.entryTitleArea}>
                              <strong className={styles.entryVersionName}>
                                {item.versionNumber > 0 ? `版本 ${item.versionNumber}` : item.title}
                              </strong>
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
                              src="/icons/chevron-right.svg"
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
                                  <strong className={styles.metricValue}>{item.budget}</strong>
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
                                  <strong className={styles.metricValue}>{item.walking}</strong>
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
                  <span>调整 {currentDiff.adjustedCount} 项</span>
                </div>

                <div className={styles.statDivider} />

                <div className={styles.statSegment}>
                  <span className={styles.statPillIconCoral}>⇄</span>
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
                {currentDiff.dayGroups.map((group) => (
                  <div key={group.dayNumber} className={styles.dayGroupSection}>
                    <h3 className={styles.dayGroupTitle}>{group.dayTitle}</h3>

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
                              <strong className={styles.changeTitle}>{change.title}</strong>
                              <span className={styles.changeSubtitle}>{change.subtitle}</span>
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
                ))}

                {/* Unchanged Activities Accordion */}
                <div className={styles.unchangedBox}>
                  <button
                    type="button"
                    className={styles.unchangedHeader}
                    onClick={() => setIsUnchangedExpanded(!isUnchangedExpanded)}
                    aria-expanded={isUnchangedExpanded}
                  >
                    <span>其余活动保持不变 (共 {currentDiff.unchangedActivities.length} 项)</span>
                    <span
                      className={`${styles.unchangedChevron} ${
                        isUnchangedExpanded ? styles.unchangedChevronOpen : ""
                      }`}
                    >
                      ⌄
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
                            <span className={styles.unchangedBullet}>•</span>
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
                    content: `正在展示 ${selectedVersionId.toUpperCase()} 的完整时间线、所有活动、预算结构与路线点位信息。`,
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
                  src="/icons/copy-id.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.mutedIcon}
                />
                <span>与其他版本比较</span>
              </button>

              <button
                type="button"
                className={styles.restoreBtn}
                onClick={() => handleRestoreVersion(TIMELINE_DATA[0])}
              >
                <Image
                  src="/icons/feedback-chat.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.mutedIcon}
                />
                <span>恢复为新版本</span>
              </button>
            </div>
          </main>
        </div>
      </div>

      {/* Snapshot Modal */}
      {modalState?.open && (
        <div className={styles.modalOverlay} onClick={() => setModalState(null)}>
          <div className={styles.modalBox} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>{modalState.title}</h3>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setModalState(null)}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalBody}>
              <p>{modalState.content}</p>
              <div className={styles.modalSnapshotArea}>
                <div className={styles.snapshotBadge}>不可变快照记录</div>
                <ul>
                  <li>总天数：5 天 4 晚 (2026-10-01 ~ 2026-10-05)</li>
                  <li>活动总数：18 个结构化活动 ({currentDiff.retentionRate}% 保留率)</li>
                  <li>总预算：¥8,460 (低于上限 ¥10,000)</li>
                  <li>总步行距离：38.6 km (每日平均 7.7 km)</li>
                </ul>
              </div>
            </div>
            <div className={styles.modalFooter}>
              <button
                type="button"
                className={styles.modalConfirmBtn}
                onClick={() => setModalState(null)}
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
