"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal, flushSync } from "react-dom";

import {
  getCurrentPlan,
  getTrip,
  submitManualPlanEdits,
  submitWalkingFeedback,
  type ManualActivityEdit,
  type PlanVersionResponse,
  type TripResponse,
} from "@/lib/api/trips";
import styles from "./itinerary-editor.module.css";

const REPLACEMENT_SUGGESTIONS = [
  "浅草寺",
  "东京国立博物馆",
  "秋叶原",
  "teamLab Borderless",
  "明治神宫",
  "SHIBUYA SKY",
];

type EditableActivity = ManualActivityEdit & {
  originalTitle: string;
  originalStart: string;
  originalEnd: string;
};

type ActivityDialogState = {
  mode: "add" | "edit";
  activityId: string | null;
};

type ActivityFormState = {
  title: string;
  start_time: string;
  end_time: string;
};

type ViewTransitionDocument = Document & {
  startViewTransition?: (update: () => void) => void;
};

type EditableDay = {
  date: string;
  dayNumber: number;
  theme: string;
  activities: EditableActivity[];
};

function clock(value: string) {
  return new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function shiftClock(value: string, minutes: number) {
  const [hours, currentMinutes] = value.split(":").map(Number);
  const total = Math.min(
    23 * 60 + 59,
    Math.max(0, hours * 60 + currentMinutes + minutes),
  );
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function activityIcon(title: string) {
  if (/餐|料理|咖啡/.test(title)) return "/icons/meal.svg";
  if (/博物馆|美术馆|museum/i.test(title)) return "/icons/museum.svg";
  return "/icons/attraction.svg";
}

function dayCaption(dayNumber: number, date: string) {
  const weekday = new Intl.DateTimeFormat("zh-CN", {
    weekday: "short",
    timeZone: "Asia/Tokyo",
  }).format(new Date(`${date}T00:00:00+09:00`));
  return `Day ${dayNumber} · ${date.slice(5).replace("-", "/")} ${weekday}`;
}

function createDraft(plan: PlanVersionResponse): EditableDay[] {
  return plan.itinerary.days.map((day) => ({
    date: day.date,
    dayNumber: day.day_number,
    theme: day.theme,
    activities: day.activities
      .filter((activity) => activity.kind !== "transfer")
      .map((activity) => ({
        id: activity.id,
        title: activity.title,
        originalTitle: activity.title,
        start_time: clock(activity.start_at),
        end_time: clock(activity.end_at),
        originalStart: clock(activity.start_at),
        originalEnd: clock(activity.end_at),
        removed: false,
        is_new: false,
      })),
  }));
}

export function ItineraryEditor({ tripId }: { tripId: string }) {
  const router = useRouter();
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [plan, setPlan] = useState<PlanVersionResponse | null>(null);
  const [days, setDays] = useState<EditableDay[]>([]);
  const [editMode, setEditMode] = useState<"ai" | "manual">("ai");
  const [selectedDay, setSelectedDay] = useState(0);
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(
    null,
  );
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draggedActivityId, setDraggedActivityId] = useState<string | null>(
    null,
  );
  const lastDragTargetId = useRef<string | null>(null);
  const [activityDialog, setActivityDialog] =
    useState<ActivityDialogState | null>(null);
  const [constraintDialogOpen, setConstraintDialogOpen] = useState(false);
  const [walkingLimit, setWalkingLimit] = useState(3000);
  const [activityForm, setActivityForm] = useState<ActivityFormState>({
    title: REPLACEMENT_SUGGESTIONS[0],
    start_time: "09:00",
    end_time: "10:00",
  });

  useEffect(() => {
    let active = true;
    Promise.all([getTrip(tripId), getCurrentPlan(tripId)])
      .then(([tripResult, planResult]) => {
        if (!active) return;
        const draft = createDraft(planResult);
        setTrip(tripResult);
        setPlan(planResult);
        setDays(draft);
        setWalkingLimit(
          tripResult.constraints.max_walking_meters_per_day ?? 3000,
        );
        setSelectedActivityId(draft[0]?.activities[0]?.id ?? null);
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "读取计划失败");
      });
    return () => {
      active = false;
    };
  }, [tripId]);

  useEffect(() => {
    if (!activityDialog && !constraintDialogOpen) return;
    const bodyOverflow = document.body.style.overflow;
    const documentOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = bodyOverflow;
      document.documentElement.style.overflow = documentOverflow;
    };
  }, [activityDialog, constraintDialogOpen]);

  const day = days[selectedDay];
  const selectedActivity = day?.activities.find(
    (item) => item.id === selectedActivityId,
  );
  const unchangedInDay = day
    ? day.activities.filter(
        (activity) =>
          !activity.is_new &&
          !activity.removed &&
          activity.title === activity.originalTitle &&
          activity.start_time === activity.originalStart &&
          activity.end_time === activity.originalEnd,
      ).length
    : 0;
  const changedInDay = day
    ? day.activities.filter(
        (activity) =>
          activity.is_new ||
          activity.removed ||
          activity.title !== activity.originalTitle ||
          activity.start_time !== activity.originalStart ||
          activity.end_time !== activity.originalEnd,
      ).length
    : 0;
  const changedCount = useMemo(
    () =>
      days.reduce(
        (total, item) =>
          total +
          item.activities.filter(
            (activity) =>
              activity.removed ||
              activity.is_new ||
              activity.title !== activity.originalTitle ||
              activity.start_time !== activity.originalStart ||
              activity.end_time !== activity.originalEnd,
          ).length,
        0,
      ),
    [days],
  );
  const changeStats = useMemo(() => {
    const activities = days.flatMap((item) => item.activities);
    const added = activities.filter((item) => item.is_new && !item.removed).length;
    const removed = activities.filter(
      (item) => !item.is_new && item.removed,
    ).length;
    const replaced = activities.filter(
      (item) => !item.is_new && !item.removed && item.title !== item.originalTitle,
    ).length;
    const rescheduled = activities.filter(
      (item) =>
        !item.is_new &&
        !item.removed &&
        (item.start_time !== item.originalStart || item.end_time !== item.originalEnd),
    ).length;
    const preserved = activities.filter(
      (item) =>
        !item.is_new &&
        !item.removed &&
        item.title === item.originalTitle &&
        item.start_time === item.originalStart &&
        item.end_time === item.originalEnd,
    ).length;
    return {
      preserved,
      adjusted: new Set(
        activities
          .filter(
            (item) =>
              !item.is_new &&
              !item.removed &&
              (item.title !== item.originalTitle ||
                item.start_time !== item.originalStart ||
                item.end_time !== item.originalEnd),
          )
          .map((item) => item.id),
      ).size,
      removed,
      added,
      replaced,
      rescheduled,
      retention: activities.filter((item) => !item.is_new).length
        ? Math.round(
            ((activities.filter((item) => !item.is_new).length - removed) /
              activities.filter((item) => !item.is_new).length) *
              100,
          )
        : 100,
    };
  }, [days]);

  function updateActivity(id: string, next: Partial<EditableActivity>) {
    setDays((current) =>
      current.map((item, dayIndex) =>
        dayIndex === selectedDay
          ? {
              ...item,
              activities: item.activities.map((activity) =>
                activity.id === id ? { ...activity, ...next } : activity,
              ),
            }
          : item,
      ),
    );
    setSavedVersion(null);
  }

  function moveActivity(id: string, direction: -1 | 1) {
    setDays((current) =>
      current.map((item, dayIndex) => {
        if (dayIndex !== selectedDay) return item;
        const activities = [...item.activities];
        const index = activities.findIndex((activity) => activity.id === id);
        const target = index + direction;
        if (index < 0 || target < 0 || target >= activities.length) return item;
        const firstTime = {
          start_time: activities[index].start_time,
          end_time: activities[index].end_time,
        };
        activities[index] = {
          ...activities[index],
          start_time: activities[target].start_time,
          end_time: activities[target].end_time,
        };
        activities[target] = { ...activities[target], ...firstTime };
        [activities[index], activities[target]] = [
          activities[target],
          activities[index],
        ];
        return { ...item, activities };
      }),
    );
    setSavedVersion(null);
  }

  function previewActivityOrder(targetId: string) {
    if (
      !draggedActivityId ||
      draggedActivityId === targetId ||
      lastDragTargetId.current === targetId
    ) {
      return;
    }
    lastDragTargetId.current = targetId;
    const updateOrder = () => {
      setDays((current) =>
        current.map((item, dayIndex) => {
          if (dayIndex !== selectedDay) return item;
          const activities = [...item.activities];
          const from = activities.findIndex(
            (activity) => activity.id === draggedActivityId,
          );
          const to = activities.findIndex(
            (activity) => activity.id === targetId,
          );
          if (from < 0 || to < 0) return item;
          const timeSlots = activities.map((activity) => ({
            start_time: activity.start_time,
            end_time: activity.end_time,
          }));
          const [moved] = activities.splice(from, 1);
          activities.splice(to, 0, moved);
          return {
            ...item,
            activities: activities.map((activity, index) => ({
              ...activity,
              ...timeSlots[index],
            })),
          };
        }),
      );
    };
    const transitionDocument = document as ViewTransitionDocument;
    if (transitionDocument.startViewTransition) {
      transitionDocument.startViewTransition(() => flushSync(updateOrder));
    } else {
      updateOrder();
    }
    setSelectedActivityId(draggedActivityId);
    setSavedVersion(null);
  }

  function finishActivityDrag() {
    setDraggedActivityId(null);
    lastDragTargetId.current = null;
  }

  function openEditDialog(activity: EditableActivity) {
    setSelectedActivityId(activity.id);
    setActivityForm({
      title: activity.title,
      start_time: activity.start_time,
      end_time: activity.end_time,
    });
    setActivityDialog({ mode: "edit", activityId: activity.id });
  }

  function openAddDialog() {
    const lastActivity = day.activities.at(-1);
    const startTime = lastActivity?.end_time ?? "09:00";
    setActivityForm({
      title: REPLACEMENT_SUGGESTIONS[0],
      start_time: startTime,
      end_time: shiftClock(startTime, 60),
    });
    setActivityDialog({ mode: "add", activityId: null });
  }

  function saveActivityDialog() {
    if (!activityDialog) return;
    if (activityForm.end_time <= activityForm.start_time) {
      setError("结束时间必须晚于开始时间");
      return;
    }
    setError(null);
    if (activityDialog.mode === "edit" && activityDialog.activityId) {
      updateActivity(activityDialog.activityId, activityForm);
    } else {
      const activity: EditableActivity = {
        id: crypto.randomUUID(),
        ...activityForm,
        originalTitle: "未安排",
        originalStart: "--:--",
        originalEnd: "--:--",
        removed: false,
        is_new: true,
      };
      setDays((current) =>
        current.map((item, dayIndex) =>
          dayIndex === selectedDay
            ? {
                ...item,
                activities: [...item.activities, activity].sort((left, right) =>
                  left.start_time.localeCompare(right.start_time),
                ),
              }
            : item,
        ),
      );
      setSelectedActivityId(activity.id);
      setSavedVersion(null);
    }
    setActivityDialog(null);
  }

  function shiftSelected(minutes: number) {
    if (!selectedActivity) return;
    updateActivity(selectedActivity.id, {
      start_time: shiftClock(selectedActivity.start_time, minutes),
      end_time: shiftClock(selectedActivity.end_time, minutes),
    });
    setChatLog((current) => [
      ...current,
      `已将“${selectedActivity.title}”${minutes < 0 ? "提前" : "推迟"}${Math.abs(minutes)}分钟。`,
    ]);
  }

  function sendAgentMessage() {
    if (!message.trim()) return;
    setChatLog((current) => [
      ...current,
      `你：${message.trim()}`,
      "Agent：请选择下方明确动作，我会把它转成可验证的行程编辑。",
    ]);
    setMessage("");
  }

  async function saveVersion() {
    if (!plan) return;
    setPending(true);
    setError(null);
    try {
      const response = await submitManualPlanEdits(
        tripId,
        plan.version,
        days.map((item) => ({
          date: item.date,
          activities: item.activities.map(
            ({ id, title, start_time, end_time, removed, is_new }) => ({
              id,
              title,
              start_time,
              end_time,
              removed,
              is_new,
            }),
          ),
        })),
      );
      setSavedVersion(response.plan.version);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "保存新版本失败");
    } finally {
      setPending(false);
    }
  }

  async function submitConstraintFeedback() {
    if (!plan) return;
    setPending(true);
    setError(null);
    try {
      const feedback = await submitWalkingFeedback(
        tripId,
        plan.version,
        walkingLimit,
        `将每天步行上限调整为 ${walkingLimit} 米`,
      );
      const [tripResult, planResult] = await Promise.all([
        getTrip(tripId),
        getCurrentPlan(tripId),
      ]);
      const draft = createDraft(planResult);
      setTrip(tripResult);
      setPlan(planResult);
      setDays(draft);
      setSelectedDay(0);
      setSelectedActivityId(draft[0]?.activities[0]?.id ?? null);
      setSavedVersion(
        feedback.planning_run?.result_plan_version ?? planResult.version,
      );
      setChatLog((current) => [
        ...current,
        `你：将每天步行上限调整为 ${walkingLimit} 米`,
        `Agent：已重新检查约束并生成版本 ${planResult.version}。`,
      ]);
      setConstraintDialogOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交约束反馈失败");
    } finally {
      setPending(false);
    }
  }

  if (error && !plan) return <main className={styles.state}>{error}</main>;
  if (!trip || !plan || !day)
    return <main className={styles.state}>正在准备行程编辑器…</main>;

  return (
    <main className={styles.page}>
      <div className={styles.topArea}>
        <header className={styles.hero}>
          <div>
            <p>
              {trip.destination}行程 · 版本 {plan.version}
            </p>
            <h1>编辑你的每日行程</h1>
            <span>调整顺序、时间和游玩景点，保存时生成新版本。</span>
          </div>
          <Link href={`/trips/${tripId}`}>返回详情</Link>
        </header>

        <div
          className={`${styles.modeSwitch} ${editMode === "manual" ? styles.manualModeSelected : ""}`}
          role="tablist"
          aria-label="选择修改方式"
        >
        <button
          aria-selected={editMode === "ai"}
          className={editMode === "ai" ? styles.activeMode : undefined}
          onClick={() => setEditMode("ai")}
          role="tab"
          type="button"
        >
          <Image
            src="/icons/adjustment-sliders.svg"
            width={22}
            height={22}
            alt=""
          />
          <span>
            <strong>AI 修改</strong>
            <small>通过对话和明确动作调整行程</small>
          </span>
        </button>
        <button
          aria-selected={editMode === "manual"}
          className={editMode === "manual" ? styles.activeMode : undefined}
          onClick={() => setEditMode("manual")}
          role="tab"
          type="button"
        >
          <Image src="/icons/edit-square.svg" width={22} height={22} alt="" />
          <span>
            <strong>手动修改</strong>
            <small>直接编辑顺序、时间和景点</small>
          </span>
        </button>
        </div>
      </div>

      <section
        className={`${styles.workspace} ${editMode === "manual" ? styles.manualWorkspace : ""}`}
      >
        {editMode === "ai" && (
          <aside className={styles.agentPanel}>
            <header>
              <span>A</span>
              <div>
                <strong>行程调整 Agent</strong>
                <small>
                  当前操作：{selectedActivity?.title ?? "请选择活动"}
                </small>
              </div>
              <button
                className={styles.agentConstraintButton}
                onClick={() => setConstraintDialogOpen(true)}
                type="button"
              >
                调整约束
              </button>
            </header>
            <div className={styles.chat}>
              <article className={styles.agentMessage}>
                <span aria-hidden="true">A</span>
                <p>
                  选择右侧的活动，然后告诉我你想怎样调整。我会把操作同步到修改对比。
                </p>
              </article>
              {chatLog.map((item, index) => {
                const isUser = item.startsWith("你：");
                const content = item.replace(/^(你|Agent)：/, "");
                return (
                  <article
                    className={
                      isUser ? styles.userMessage : styles.agentMessage
                    }
                    key={`${item}-${index}`}
                  >
                    <span aria-hidden="true">{isUser ? "旅" : "A"}</span>
                    <p>{content}</p>
                  </article>
                );
              })}
            </div>
            <div className={styles.agentActions}>
              <button
                disabled={!selectedActivity}
                onClick={() => shiftSelected(-30)}
                type="button"
              >
                提前 30 分钟
              </button>
              <button
                disabled={!selectedActivity}
                onClick={() => shiftSelected(30)}
                type="button"
              >
                推迟 30 分钟
              </button>
              <button
                disabled={!selectedActivity}
                onClick={() =>
                  selectedActivity && moveActivity(selectedActivity.id, -1)
                }
                type="button"
              >
                向前移动
              </button>
              <button
                disabled={!selectedActivity}
                onClick={() =>
                  selectedActivity && moveActivity(selectedActivity.id, 1)
                }
                type="button"
              >
                向后移动
              </button>
              <button
                disabled={!selectedActivity}
                onClick={() =>
                  selectedActivity &&
                  updateActivity(selectedActivity.id, {
                    removed: !selectedActivity.removed,
                  })
                }
                type="button"
              >
                {selectedActivity?.removed ? "恢复活动" : "删除活动"}
              </button>
              <label className={styles.agentReplace}>
                替换当前景点
                <select
                  disabled={!selectedActivity}
                  value={selectedActivity?.title ?? ""}
                  onChange={(event) =>
                    selectedActivity &&
                    updateActivity(selectedActivity.id, {
                      title: event.target.value,
                    })
                  }
                >
                  {selectedActivity && (
                    <option value={selectedActivity.originalTitle}>
                      {selectedActivity.originalTitle}
                    </option>
                  )}
                  {REPLACEMENT_SUGGESTIONS.filter(
                    (name) => name !== selectedActivity?.originalTitle,
                  ).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className={styles.composer}>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="例如：把这个景点安排到下午…"
              />
              <button onClick={sendAgentMessage} type="button">
                发送
              </button>
            </div>
          </aside>
        )}

        {editMode === "manual" && (
          <section className={styles.manualPanel}>
            <nav className={styles.dayTabs} aria-label="选择编辑日期">
              {days.map((item, index) => (
                <button
                  className={
                    selectedDay === index ? styles.activeDay : undefined
                  }
                  key={item.date}
                  onClick={() => {
                    setSelectedDay(index);
                    setSelectedActivityId(item.activities[0]?.id ?? null);
                  }}
                  type="button"
                >
                  Day {item.dayNumber}
                  <small>{item.date.slice(5)}</small>
                </button>
              ))}
            </nav>
            <header className={styles.manualHeader}>
              <div>
                <h2>
                  Day {day.dayNumber} · {day.theme}
                </h2>
                <p>按住卡片上下拖拽调整顺序；点击修改再编辑地点与时间。</p>
              </div>
              <button onClick={openAddDialog} type="button">
                ＋ 添加地点
              </button>
            </header>
            <ol className={styles.dragList}>
              {day.activities.map((activity, index) => (
                <li
                  className={`${selectedActivityId === activity.id ? styles.selectedDragCard : ""} ${activity.removed ? styles.removedDragCard : ""} ${draggedActivityId === activity.id ? styles.draggingCard : ""}`}
                  draggable={!activity.removed}
                  key={activity.id}
                  style={{
                    viewTransitionName: `activity-${activity.id.replaceAll("-", "")}`,
                  }}
                  onClick={() => setSelectedActivityId(activity.id)}
                  onDragEnd={finishActivityDrag}
                  onDragEnter={() => previewActivityOrder(activity.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDragStart={() => {
                    lastDragTargetId.current = null;
                    setDraggedActivityId(activity.id);
                  }}
                  onDrop={finishActivityDrag}
                >
                  <span className={styles.dragHandle} aria-hidden="true">
                    ⠿
                  </span>
                  <b>{String(index + 1).padStart(2, "0")}</b>
                  <time>
                    {activity.start_time}–{activity.end_time}
                  </time>
                  <div>
                    <strong>{activity.title}</strong>
                    <small>
                      {activity.is_new
                        ? "新增地点"
                        : activity.removed
                          ? "已标记删除"
                          : "拖拽可调整游览顺序"}
                    </small>
                  </div>
                  <button
                    className={styles.editActivityButton}
                    onClick={(event) => {
                      event.stopPropagation();
                      openEditDialog(activity);
                    }}
                    type="button"
                  >
                    修改
                  </button>
                </li>
              ))}
            </ol>
          </section>
        )}

          <section className={styles.aiPreviewPanel}>
            <nav className={styles.dayTabs} aria-label="选择预览日期">
              {days.map((item, index) => (
                <button
                  className={
                    selectedDay === index ? styles.activeDay : undefined
                  }
                  key={item.date}
                  onClick={() => {
                    setSelectedDay(index);
                    setSelectedActivityId(item.activities[0]?.id ?? null);
                  }}
                  type="button"
                >
                  Day {item.dayNumber}
                  <small>{item.date.slice(5)}</small>
                </button>
              ))}
            </nav>
            <header className={styles.previewHeading}>
              <h2>{editMode === "ai" ? "本次变更" : "手动修改对比"}</h2>
            </header>
            <div className={styles.changeMetrics}>
              <div>
                <b>✓</b>
                <span>
                  保留<strong>{changeStats.preserved} 项</strong>
                </span>
              </div>
              <div>
                <b>≋</b>
                <span>
                  调整<strong>{changeStats.adjusted} 项</strong>
                </span>
              </div>
              <div>
                <b>−</b>
                <span>
                  移除<strong>{changeStats.removed} 项</strong>
                </span>
              </div>
              <div>
                <b>＋</b>
                <span>
                  新增<strong>{changeStats.added} 项</strong>
                </span>
              </div>
              <div>
                <i
                  style={
                    {
                      "--retention": `${changeStats.retention * 3.6}deg`,
                    } as React.CSSProperties
                  }
                />
                <span>
                  计划保留率<strong>{changeStats.retention}%</strong>
                </span>
              </div>
            </div>
            <div className={styles.timelineComparison}>
              <header className={styles.comparisonHeaders}>
                <div>
                  <strong>{dayCaption(day.dayNumber, day.date)}</strong>
                  <span>调整前</span>
                </div>
                <div>
                  <strong>{dayCaption(day.dayNumber, day.date)}</strong>
                  <span>调整后</span>
                </div>
              </header>

              <div className={styles.comparisonColumns}>
                <div className={styles.comparisonColumnList}>
                  {[...day.activities]
                    .filter((activity) => !activity.is_new)
                    .sort((left, right) =>
                      left.originalStart.localeCompare(right.originalStart),
                    )
                    .map((activity) => {
                      const changed =
                        activity.removed ||
                        activity.title !== activity.originalTitle ||
                        activity.start_time !== activity.originalStart ||
                        activity.end_time !== activity.originalEnd;
                      const stateClass = activity.removed
                        ? styles.removedComparisonRow
                        : styles.adjustedComparisonRow;
                      return (
                        <div
                          className={`${styles.comparisonOriginalItem} ${changed ? stateClass : styles.unchangedComparisonRow}`}
                          key={activity.id}
                        >
                          <div className={styles.comparisonSlot}>
                          <button
                            className={
                              selectedActivityId === activity.id
                                ? styles.selectedComparisonCard
                                : undefined
                            }
                            onClick={() => setSelectedActivityId(activity.id)}
                            type="button"
                          >
                            <time>{activity.originalStart}</time>
                            <i aria-hidden="true" />
                            <Image
                              alt=""
                              height={20}
                              src={activityIcon(activity.originalTitle)}
                              width={20}
                            />
                            <span>
                              <strong>{activity.originalTitle}</strong>
                              <small>
                                {activity.originalStart}–{activity.originalEnd}
                              </small>
                            </span>
                          </button>
                          </div>
                        </div>
                      );
                    })}
                </div>

                <div className={styles.comparisonColumnList}>
                  {day.activities
                    .filter(
                      (activity) =>
                        activity.is_new ||
                        activity.removed ||
                        activity.title !== activity.originalTitle ||
                        activity.start_time !== activity.originalStart ||
                        activity.end_time !== activity.originalEnd,
                    )
                    .map((activity) => {
                      const stateClass = activity.is_new
                        ? styles.addedComparisonRow
                        : activity.removed
                          ? styles.removedComparisonRow
                          : styles.adjustedComparisonRow;
                      return (
                        <div
                          className={`${styles.comparisonChangedItem} ${stateClass}`}
                          key={activity.id}
                        >
                          <span
                            className={styles.rowChangeArrow}
                            aria-hidden="true"
                          >
                            <i />
                          </span>
                          <div className={styles.comparisonSlot}>
                          <button
                            className={
                              selectedActivityId === activity.id
                                ? styles.selectedComparisonCard
                                : undefined
                            }
                            onClick={() => setSelectedActivityId(activity.id)}
                            type="button"
                          >
                            <time>
                              {activity.removed ? "—" : activity.start_time}
                            </time>
                            <i aria-hidden="true" />
                            {!activity.removed && (
                              <Image
                                alt=""
                                height={20}
                                src={activityIcon(activity.title)}
                                width={20}
                              />
                            )}
                            <span>
                              <strong>
                                {activity.removed ? "已删除" : activity.title}
                              </strong>
                              <small>
                                {activity.removed
                                  ? `原地点：${activity.originalTitle}`
                                  : activity.is_new
                                    ? "新增行程地点"
                                    : `${activity.start_time}–${activity.end_time}`}
                              </small>
                            </span>
                          </button>
                          </div>
                        </div>
                      );
                    })}
                  {changedInDay === 0 && (
                    <p className={styles.noChangedItems}>暂无调整内容</p>
                  )}
                </div>
              </div>
              <footer className={styles.unchangedSummary}>
                ›　其中 {unchangedInDay} 项保持不变，不重复显示调整后内容
              </footer>
            </div>

            <section className={styles.previewConstraints}>
              <h3>约束检查</h3>
              <div>
                <span>✓　结束时间符合要求</span>
                <span>✓　预算变化仍在范围内</span>
                <span>✓　预计步行距离符合要求</span>
                <span>ⓘ　保存版本后将重新计算路线</span>
              </div>
            </section>
          </section>
      </section>

      {activityDialog &&
        createPortal(
          <div
            className={styles.dialogBackdrop}
            onMouseDown={(event) => {
              if (event.currentTarget === event.target) setActivityDialog(null);
            }}
            role="presentation"
          >
            <section
              aria-labelledby="activity-dialog-title"
              aria-modal="true"
              className={styles.activityDialog}
              role="dialog"
            >
              <header>
                <div>
                  <small>
                    {activityDialog.mode === "add"
                      ? "新增行程节点"
                      : "编辑行程节点"}
                  </small>
                  <h2 id="activity-dialog-title">
                    {activityDialog.mode === "add"
                      ? "添加游玩地点"
                      : "修改地点与时间"}
                  </h2>
                </div>
                <button
                  aria-label="关闭修改窗口"
                  onClick={() => setActivityDialog(null)}
                  type="button"
                >
                  ×
                </button>
              </header>
              <div className={styles.dialogFields}>
                <label>
                  游玩地点
                  <select
                    value={activityForm.title}
                    onChange={(event) =>
                      setActivityForm((current) => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                  >
                    {!REPLACEMENT_SUGGESTIONS.includes(activityForm.title) && (
                      <option value={activityForm.title}>
                        {activityForm.title}
                      </option>
                    )}
                    {REPLACEMENT_SUGGESTIONS.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
                <div>
                  <label>
                    开始时间
                    <input
                      type="time"
                      value={activityForm.start_time}
                      onChange={(event) =>
                        setActivityForm((current) => ({
                          ...current,
                          start_time: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label>
                    结束时间
                    <input
                      type="time"
                      value={activityForm.end_time}
                      onChange={(event) =>
                        setActivityForm((current) => ({
                          ...current,
                          end_time: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>
              </div>
              <p>保存后不会立即提交，而是在右侧生成修改前后的对比。</p>
              {error && (
                <p className={styles.error} role="alert">
                  {error}
                </p>
              )}
              <footer>
                {activityDialog.mode === "edit" &&
                  activityDialog.activityId && (
                    <button
                      className={styles.dialogDeleteButton}
                      onClick={() => {
                        const activity = day.activities.find(
                          (item) => item.id === activityDialog.activityId,
                        );
                        updateActivity(activityDialog.activityId!, {
                          removed: !activity?.removed,
                        });
                        setActivityDialog(null);
                      }}
                      type="button"
                    >
                      {day.activities.find(
                        (item) => item.id === activityDialog.activityId,
                      )?.removed
                        ? "恢复地点"
                        : "删除地点"}
                    </button>
                  )}
                <span />
                <button onClick={() => setActivityDialog(null)} type="button">
                  取消
                </button>
                <button
                  className={styles.dialogSaveButton}
                  onClick={saveActivityDialog}
                  type="button"
                >
                  保存到修改草稿
                </button>
              </footer>
            </section>
          </div>,
          document.body,
        )}

      {constraintDialogOpen &&
        createPortal(
          <div
            className={styles.dialogBackdrop}
            onMouseDown={(event) => {
              if (event.currentTarget === event.target) {
                setConstraintDialogOpen(false);
              }
            }}
            role="presentation"
          >
            <section
              aria-labelledby="constraint-dialog-title"
              aria-modal="true"
              className={styles.activityDialog}
              role="dialog"
            >
              <header>
                <div>
                  <small>结构化反馈</small>
                  <h2 id="constraint-dialog-title">调整每日步行上限</h2>
                </div>
                <button
                  aria-label="关闭约束窗口"
                  onClick={() => setConstraintDialogOpen(false)}
                  type="button"
                >
                  ×
                </button>
              </header>
              <div className={styles.walkingConstraintField}>
                <label htmlFor="walking-limit">每天最多步行</label>
                <output>{(walkingLimit / 1000).toFixed(1)} 公里</output>
                <input
                  id="walking-limit"
                  max="12000"
                  min="1000"
                  onChange={(event) => setWalkingLimit(Number(event.target.value))}
                  step="500"
                  type="range"
                  value={walkingLimit}
                />
                <small>提交后会保留旧版本，并基于当前版本重新规划。</small>
              </div>
              {error && (
                <p className={styles.error} role="alert">
                  {error}
                </p>
              )}
              <footer>
                <span />
                <span />
                <button
                  onClick={() => setConstraintDialogOpen(false)}
                  type="button"
                >
                  取消
                </button>
                <button
                  className={styles.dialogSaveButton}
                  disabled={pending}
                  onClick={() => void submitConstraintFeedback()}
                  type="button"
                >
                  {pending ? "正在重新规划…" : "提交并生成新版本"}
                </button>
              </footer>
            </section>
          </div>,
          document.body,
        )}

      <footer className={styles.actionBar}>
        <div>
          <span>✓</span>
          <strong>
            {savedVersion
              ? `版本 ${savedVersion} 已生成，等待你确认。`
              : `版本 ${plan.version} 的修改草稿尚未保存。`}
          </strong>
        </div>
        <div>
          <Link href={`/trips/${tripId}`}>放弃修改</Link>
          {savedVersion ? (
            <button onClick={() => router.push(`/trips/${tripId}`)} type="button">
              查看版本 {savedVersion}
            </button>
          ) : (
            <button
              disabled={pending || changedCount === 0}
              onClick={() => void saveVersion()}
              type="button"
            >
              {pending
                ? "正在生成新版本…"
                : editMode === "ai"
                  ? "生成 AI 修改版本"
                  : "保存手动修改版本"}
            </button>
          )}
        </div>
        {error && <p className={styles.error} role="alert">{error}</p>}
      </footer>
    </main>
  );
}
