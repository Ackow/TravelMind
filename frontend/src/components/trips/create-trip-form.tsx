"use client";

import { useEffect, useState, type SubmitEvent } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import {
  createTrip,
  type DietaryPreference,
  type Pace,
  type TransportMode,
  type TripCreateRequest,
} from "@/lib/api/trips";

import { CityCombobox } from "./city-combobox";
import { DateRangePicker } from "./date-range-picker";
import { MultiSelectDropdown } from "./multi-select-dropdown";
import styles from "./create-trip-form.module.css";

const INTERESTS = ["动漫", "美食", "城市漫步", "博物馆", "自然风景", "夜生活"];
const DIETARY_OPTIONS: Array<{ value: DietaryPreference; label: string }> = [
  { value: "vegetarian", label: "素食" },
  { value: "vegan", label: "纯素" },
  { value: "halal", label: "清真" },
  { value: "gluten_free", label: "无麸质" },
  { value: "no_pork", label: "不吃猪肉" },
  { value: "no_beef", label: "不吃牛肉" },
  { value: "seafood_free", label: "不吃海鲜" },
  { value: "nut_free", label: "坚果过敏" },
];
const TRANSPORT_OPTIONS: Array<{ value: TransportMode; label: string }> = [
  { value: "public_transit", label: "公共交通" },
  { value: "walking", label: "步行" },
  { value: "taxi", label: "出租车" },
  { value: "driving", label: "自驾" },
  { value: "cycling", label: "骑行" },
  { value: "mixed", label: "多种方式" },
];
const PACES: Array<{ value: Pace; label: string; description: string }> = [
  { value: "relaxed", label: "轻松", description: "留更多空白" },
  { value: "balanced", label: "均衡", description: "张弛有度" },
  { value: "packed", label: "紧凑", description: "尽量多体验" },
];

const DEFAULT_REQUEST: TripCreateRequest = {
  origin: "",
  destination: "",
  destination_timezone: "Asia/Shanghai",
  date_range: { start_date: "", end_date: "" },
  travelers: 2,
  preferences: {
    interests: [],
    avoid: [],
    dietary: [],
    transport_modes: ["public_transit", "walking"],
    accommodation_notes: "",
    pace: "balanced",
    must_visit_place_names: [],
  },
  constraints: {
    total_budget: { amount: 500_000, currency: "CNY" },
    budget_is_hard_limit: true,
    daily_start_time: "09:00",
    daily_end_time: "21:00",
    max_walking_meters_per_day: 12_000,
    max_activities_per_day: 5,
    minimum_transfer_buffer_minutes: 10,
    rest_minutes_per_day: 60,
    required_place_names: [],
    excluded_place_names: [],
    accessible_only: false,
  },
  locale: "zh-CN",
  display_currency: "CNY",
  notes: null,
};

function parseNames(value: string): string[] {
  return value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatMoney(amount: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

function countTripDays(startDate: string, endDate: string): number {
  if (!startDate || !endDate || !startDate.includes("-") || !endDate.includes("-")) {
    return 0;
  }
  const [startYear, startMonth, startDay] = startDate.split("-").map(Number);
  const [endYear, endMonth, endDay] = endDate.split("-").map(Number);
  const milliseconds =
    Date.UTC(endYear, endMonth - 1, endDay) -
    Date.UTC(startYear, startMonth - 1, startDay);
  return Math.max(1, Math.round(milliseconds / 86_400_000) + 1);
}

export function CreateTripForm() {
  const router = useRouter();
  const [activeStep, setActiveStep] = useState<1 | 2 | 3 | 4>(1);
  const [request, setRequest] = useState(DEFAULT_REQUEST);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draftStatus, setDraftStatus] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(true);
  const selectedInterests = request.preferences.interests.map(
    (item) => item.value,
  );
  const tripDays = countTripDays(
    request.date_range.start_date,
    request.date_range.end_date,
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = window.localStorage.getItem("travelmind-trip-draft");
      if (!saved) return;
      try {
        setRequest(JSON.parse(saved) as TripCreateRequest);
        setDraftStatus("已恢复上次保存的草稿");
      } catch {
        window.localStorage.removeItem("travelmind-trip-draft");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  function saveDraft() {
    window.localStorage.setItem(
      "travelmind-trip-draft",
      JSON.stringify(request),
    );
    setDraftStatus(
      `草稿已保存 · ${new Intl.DateTimeFormat("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date())}`,
    );
  }

  function updatePreferences(next: Partial<TripCreateRequest["preferences"]>) {
    setRequest((current) => ({
      ...current,
      preferences: { ...current.preferences, ...next },
    }));
  }

  function updateConstraints(next: Partial<TripCreateRequest["constraints"]>) {
    setRequest((current) => ({
      ...current,
      constraints: { ...current.constraints, ...next },
    }));
  }

  function toggleInterest(value: string) {
    const exists = request.preferences.interests.some(
      (item) => item.value === value,
    );
    const interests = exists
      ? request.preferences.interests.filter((item) => item.value !== value)
      : [...request.preferences.interests, { value, weight: 0.7 }];
    updatePreferences({ interests });
  }

  function updateInterestWeight(value: string, weight: number) {
    updatePreferences({
      interests: request.preferences.interests.map((item) =>
        item.value === value ? { ...item, weight } : item,
      ),
    });
  }

  function changeTravelers(delta: number) {
    setRequest((current) => ({
      ...current,
      travelers: Math.min(6, Math.max(1, current.travelers + delta)),
    }));
  }

  function handleProceedToStep2() {
    if (!request.origin.trim()) {
      setError("请填写或选择出发地城市");
      return;
    }
    if (!request.destination.trim()) {
      setError("请填写或选择目的地城市");
      return;
    }
    if (tripDays < 3 || tripDays > 7) {
      setError(
        `当前 MVP 阶段仅支持 3～7 天行程规划（当前选择了 ${tripDays > 0 ? `${tripDays} 天` : "未完整选择日期"}，请点击调整出行日期）`,
      );
      return;
    }
    setError(null);
    setActiveStep(2);
  }

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activeStep !== 4) {
      return;
    }
    if (tripDays < 3 || tripDays > 7) {
      setError(`行程天数需在 3～7 天之间（当前选择 ${tripDays} 天）`);
      setActiveStep(1);
      return;
    }
    if (!agreedToTerms) {
      setError("请先阅读并勾选同意《用户服务协议》与《隐私政策》");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const trip = await createTrip(request);
      try {
        const stored = JSON.parse(window.localStorage.getItem("travelmind-recent-trips") || "[]");
        const updated = [trip, ...stored.filter((t: any) => t.id !== trip.id)].slice(0, 20);
        window.localStorage.setItem("travelmind-recent-trips", JSON.stringify(updated));
      } catch {
        // 忽略存储异常
      }
      window.localStorage.removeItem("travelmind-trip-draft");
      router.push(`/trips/${trip.id}/planning`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "创建旅行失败，请稍后再试。",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.steps} aria-label="创建旅行步骤">
        <button
          className={
            activeStep === 1
              ? styles.stepActive
              : activeStep > 1
                ? styles.stepComplete
                : undefined
          }
          type="button"
          onClick={() => setActiveStep(1)}
        >
          <b>1</b>基本信息
        </button>
        <i aria-hidden="true" />
        <button
          className={
            activeStep === 2
              ? styles.stepActive
              : activeStep > 2
                ? styles.stepComplete
                : undefined
          }
          type="button"
          onClick={() => setActiveStep(2)}
        >
          <b>2</b>旅行偏好
        </button>
        <i aria-hidden="true" />
        <button
          className={
            activeStep === 3
              ? styles.stepActive
              : activeStep > 3
                ? styles.stepComplete
                : undefined
          }
          type="button"
          onClick={() => setActiveStep(3)}
        >
          <b>3</b>行程约束
        </button>
        <i aria-hidden="true" />
        <button
          className={activeStep === 4 ? styles.stepActive : undefined}
          type="button"
          onClick={() => setActiveStep(4)}
        >
          <b>4</b>确认
        </button>
      </div>
      <div className={styles.content}>
        <div className={styles.mainColumn}>
          <header className={styles.heading}>
            <p>旅行请求</p>
            <h1>创建旅行</h1>
            <span>告诉我们你想怎样旅行，之后随时可以继续调整。</span>
          </header>
          {activeStep === 1 && (
            <section className={styles.card}>
              <div className={styles.cardTitle}>
                <span>01</span>
                <div>
                  <h2>去哪儿</h2>
                  <p>先确认时间、地点和同行人数。</p>
                </div>
              </div>
              <div className={styles.twoColumns}>
                <CityCombobox
                  label="出发地"
                  value={request.origin}
                  onChange={(origin) => setRequest({ ...request, origin })}
                />
                <CityCombobox
                  label="目的地"
                  value={request.destination}
                  onChange={(destination) =>
                    setRequest({ ...request, destination })
                  }
                  onSelect={(city) =>
                    setRequest((current) => ({
                      ...current,
                      destination: city.name,
                      destination_timezone:
                        city.timezone ?? current.destination_timezone,
                    }))
                  }
                />
                <DateRangePicker
                  startDate={request.date_range.start_date}
                  endDate={request.date_range.end_date}
                  onChange={(startDate, endDate) =>
                    setRequest({
                      ...request,
                      date_range: {
                        start_date: startDate,
                        end_date: endDate,
                      },
                    })
                  }
                />
                <div className={styles.travelerField}>
                  <span>同行人数</span>
                  <div className={styles.stepper}>
                    <button
                      type="button"
                      aria-label="减少一位旅行者"
                      onClick={() => changeTravelers(-1)}
                      disabled={request.travelers <= 1}
                    >
                      −
                    </button>
                    <strong>{request.travelers} 人</strong>
                    <button
                      type="button"
                      aria-label="增加一位旅行者"
                      onClick={() => changeTravelers(1)}
                      disabled={request.travelers >= 6}
                    >
                      ＋
                    </button>
                  </div>
                </div>
              </div>
              <p className={styles.inlineNote}>当前 MVP 支持 3～7 天的旅行。</p>
              <div className={styles.stepActions}>
                <button type="button" onClick={handleProceedToStep2}>
                  下一步：偏好与约束
                </button>
              </div>
            </section>
          )}
          {activeStep === 2 && (
            <section className={[styles.card, styles.preferenceCard].join(" ")}>
              <div className={styles.cardTitle}>
                <span>02</span>
                <div>
                  <h2>你喜欢什么</h2>
                  <p>选择最符合你的兴趣、节奏与出行习惯。</p>
                </div>
              </div>
              <fieldset className={styles.fieldset}>
                <legend>旅行兴趣</legend>
                <div className={styles.chips}>
                  {INTERESTS.map((interest) => {
                    const selected = selectedInterests.includes(interest);
                    return (
                      <button
                        className={selected ? styles.chipSelected : styles.chip}
                        key={interest}
                        onClick={() => toggleInterest(interest)}
                        type="button"
                        aria-pressed={selected}
                      >
                        {selected ? "✓ " : ""}
                        {interest}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
              {request.preferences.interests.length > 0 && (
                <div className={styles.weights}>
                  {request.preferences.interests.map((interest) => (
                    <label key={interest.value}>
                      <span>
                        {interest.value}
                        <small>{Math.round(interest.weight * 100)}%</small>
                      </span>
                      <input
                        type="range"
                        min="0.1"
                        max="1"
                        step="0.1"
                        value={interest.weight}
                        onChange={(event) =>
                          updateInterestWeight(
                            interest.value,
                            Number(event.target.value),
                          )
                        }
                      />
                    </label>
                  ))}
                </div>
              )}
              <fieldset className={styles.fieldset}>
                <legend>行程节奏</legend>
                <div className={styles.paceOptions}>
                  {PACES.map((pace) => (
                    <button
                      className={
                        request.preferences.pace === pace.value
                          ? styles.paceSelected
                          : styles.pace
                      }
                      key={pace.value}
                      type="button"
                      onClick={() => updatePreferences({ pace: pace.value })}
                    >
                      <strong>{pace.label}</strong>
                      <small>{pace.description}</small>
                    </button>
                  ))}
                </div>
              </fieldset>
              <div className={styles.compactPreferences}>
                <MultiSelectDropdown
                  label="允许的交通方式"
                  options={TRANSPORT_OPTIONS}
                  values={request.preferences.transport_modes}
                  onChange={(transport_modes) =>
                    updatePreferences({ transport_modes })
                  }
                />
                <MultiSelectDropdown
                  label="饮食偏好"
                  options={DIETARY_OPTIONS}
                  values={request.preferences.dietary}
                  emptyText="无特殊要求"
                  onChange={(dietary) => updatePreferences({ dietary })}
                />
                <div className={styles.twoColumns}>
                  <label>
                    不希望出现
                    <input
                      value={request.preferences.avoid.join("，")}
                      placeholder="购物，排队"
                      onChange={(event) =>
                        updatePreferences({
                          avoid: parseNames(event.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    希望尽量去
                    <input
                      value={request.preferences.must_visit_place_names.join(
                        "，",
                      )}
                      placeholder="例如想去的地标或场馆"
                      onChange={(event) =>
                        updatePreferences({
                          must_visit_place_names: parseNames(
                            event.target.value,
                          ),
                        })
                      }
                    />
                  </label>
                </div>
                <label className={styles.fullField}>
                  住宿偏好
                  <textarea
                    rows={2}
                    value={request.preferences.accommodation_notes ?? ""}
                    placeholder="例如：靠近地铁站、希望安静"
                    onChange={(event) =>
                      updatePreferences({
                        accommodation_notes: event.target.value || null,
                      })
                    }
                  />
                </label>
              </div>
              <div className={styles.stepActions}>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => setActiveStep(1)}
                >
                  上一步
                </button>
                <button type="button" onClick={() => setActiveStep(3)}>
                  下一步：行程约束
                </button>
              </div>
            </section>
          )}
          {activeStep === 3 && (
            <section className={[styles.card, styles.constraintCard].join(" ")}>
              <div className={styles.cardTitle}>
                <span>03</span>
                <div>
                  <h2>行程约束</h2>
                  <p>这些条件会被明确检查，不会被系统静默忽略。</p>
                </div>
              </div>
              <div className={styles.twoColumns}>
                <label>
                  总预算（人民币元）
                  <input
                    type="number"
                    min="1"
                    value={request.constraints.total_budget.amount / 100}
                    onChange={(event) =>
                      updateConstraints({
                        total_budget: {
                          amount: Number(event.target.value) * 100,
                          currency: "CNY",
                        },
                      })
                    }
                  />
                </label>
                <label className={styles.rangeField}>
                  <span>
                    每天最多步行
                    <strong>
                      {(request.constraints.max_walking_meters_per_day ?? 0) /
                        1000}{" "}
                      公里
                    </strong>
                  </span>
                  <input
                    type="range"
                    min="1"
                    max="50"
                    step="1"
                    value={
                      (request.constraints.max_walking_meters_per_day ?? 0) /
                      1000
                    }
                    onChange={(event) =>
                      updateConstraints({
                        max_walking_meters_per_day:
                          Number(event.target.value) * 1000,
                      })
                    }
                  />
                </label>
              </div>
              <div className={styles.advancedConstraints}>
                <h3>其他约束</h3>
                <div className={styles.twoColumns}>
                  <label>
                    每日开始时间
                    <input
                      type="time"
                      value={request.constraints.daily_start_time}
                      onChange={(event) =>
                        updateConstraints({
                          daily_start_time: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    每日最晚结束
                    <input
                      type="time"
                      value={request.constraints.daily_end_time}
                      onChange={(event) =>
                        updateConstraints({
                          daily_end_time: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    每日最多活动
                    <select
                      value={request.constraints.max_activities_per_day}
                      onChange={(event) =>
                        updateConstraints({
                          max_activities_per_day: Number(event.target.value),
                        })
                      }
                    >
                      {[3, 4, 5, 6, 7, 8].map((value) => (
                        <option key={value} value={value}>
                          {value} 项
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    换乘缓冲（分钟）
                    <select
                      value={
                        request.constraints.minimum_transfer_buffer_minutes
                      }
                      onChange={(event) =>
                        updateConstraints({
                          minimum_transfer_buffer_minutes: Number(
                            event.target.value,
                          ),
                        })
                      }
                    >
                      {[0, 10, 15, 20, 30, 45, 60].map((value) => (
                        <option key={value} value={value}>
                          {value} 分钟
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    每日休息（分钟）
                    <select
                      value={request.constraints.rest_minutes_per_day}
                      onChange={(event) =>
                        updateConstraints({
                          rest_minutes_per_day: Number(event.target.value),
                        })
                      }
                    >
                      {[0, 30, 60, 90, 120, 180, 240].map((value) => (
                        <option key={value} value={value}>
                          {value} 分钟
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    界面语言
                    <select
                      value={request.locale}
                      onChange={(event) =>
                        setRequest({ ...request, locale: event.target.value })
                      }
                    >
                      <option value="zh-CN">简体中文（zh-CN）</option>
                      <option value="en-US">English（en-US）</option>
                    </select>
                  </label>
                </div>
                <div className={styles.twoColumns}>
                  <label>
                    必须去的地点
                    <input
                      value={request.constraints.required_place_names.join(
                        "，",
                      )}
                      placeholder="用逗号分隔"
                      onChange={(event) =>
                        updateConstraints({
                          required_place_names: parseNames(event.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    必须排除的地点
                    <input
                      value={request.constraints.excluded_place_names.join(
                        "，",
                      )}
                      placeholder="用逗号分隔"
                      onChange={(event) =>
                        updateConstraints({
                          excluded_place_names: parseNames(event.target.value),
                        })
                      }
                    />
                  </label>
                </div>
                <div className={styles.checkRows}>
                  <label>
                    <input
                      type="checkbox"
                      checked={request.constraints.budget_is_hard_limit}
                      onChange={(event) =>
                        updateConstraints({
                          budget_is_hard_limit: event.target.checked,
                        })
                      }
                    />
                    总预算是不可突破的硬上限
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={request.constraints.accessible_only}
                      onChange={(event) =>
                        updateConstraints({
                          accessible_only: event.target.checked,
                        })
                      }
                    />
                    只安排无障碍友好的地点
                  </label>
                </div>
                <label className={styles.fullField}>
                  其他备注
                  <textarea
                    rows={3}
                    value={request.notes ?? ""}
                    placeholder="例如：第二天下午需要保留两个小时处理工作"
                    onChange={(event) =>
                      setRequest({
                        ...request,
                        notes: event.target.value || null,
                      })
                    }
                  />
                </label>
              </div>
              <div className={styles.stepActions}>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => setActiveStep(2)}
                >
                  上一步
                </button>
                <button type="button" onClick={() => setActiveStep(4)}>
                  下一步：确认
                </button>
              </div>
            </section>
          )}
          {activeStep === 4 && (
            <section className={[styles.card, styles.confirmCard].join(" ")}>
              <div className={styles.cardTitle}>
                <span>04</span>
                <div>
                  <h2>确认旅行请求</h2>
                  <p>提交前快速检查关键信息，创建后仍然可以继续调整。</p>
                </div>
              </div>
              <div className={styles.confirmGrid}>
                <div>
                  <span>路线</span>
                  <strong>
                    {request.origin} → {request.destination}
                  </strong>
                </div>
                <div>
                  <span>日期</span>
                  <strong>
                    {request.date_range.start_date} 至{" "}
                    {request.date_range.end_date}
                  </strong>
                </div>
                <div>
                  <span>人数</span>
                  <strong>{request.travelers} 位旅行者</strong>
                </div>
                <div>
                  <span>预算</span>
                  <strong>
                    {formatMoney(request.constraints.total_budget.amount)}
                  </strong>
                </div>
                <div>
                  <span>节奏</span>
                  <strong>
                    {
                      PACES.find(
                        (item) => item.value === request.preferences.pace,
                      )?.label
                    }
                  </strong>
                </div>
                <div>
                  <span>兴趣</span>
                  <strong>{selectedInterests.join("、") || "暂未选择"}</strong>
                </div>
              </div>
              <div className={styles.confirmHint}>
                <Image
                  aria-hidden="true"
                  src="/icons/shield-check.svg"
                  alt=""
                  width={22}
                  height={22}
                />
                <span>系统会逐项检查预算、步行距离、营业时间和交通衔接。</span>
              </div>
              <div className={styles.stepActions}>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => setActiveStep(3)}
                >
                  上一步
                </button>
              </div>
            </section>
          )}
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </div>
        <aside className={styles.summary}>
          <p className={styles.summaryLabel}>旅行摘要</p>
          <h2 className={styles.summaryRoute}>
            <span className={styles.summaryCity}>{request.origin || "出发地"}</span>
            <span className={styles.summaryArrow}>→</span>
            <span className={styles.summaryCity}>{request.destination || "目的地"}</span>
          </h2>
          <div className={styles.summaryMeta}>
            <div>
              <Image
                aria-hidden="true"
                src="/icons/calendar.svg"
                alt=""
                width={20}
                height={20}
              />
              <span>
                {tripDays} 天 {Math.max(0, tripDays - 1)} 晚
              </span>
            </div>
            <div>
              <Image
                aria-hidden="true"
                src="/icons/user.svg"
                alt=""
                width={20}
                height={20}
              />
              <span>{request.travelers} 位旅行者</span>
            </div>
            <div>
              <Image
                aria-hidden="true"
                src="/icons/wallet.svg"
                alt=""
                width={20}
                height={20}
              />
              <span>
                {formatMoney(request.constraints.total_budget.amount)} 总预算
              </span>
            </div>
          </div>
          <p className={styles.summarySectionLabel}>偏好</p>
          <div className={styles.summaryChips}>
            {selectedInterests.map((interest) => (
              <span key={interest}>{interest}</span>
            ))}
          </div>
          <p className={styles.summarySectionLabel}>不希望出现</p>
          <div className={styles.summaryChips}>
            {request.preferences.avoid.length > 0 ? (
              request.preferences.avoid.map((item) => (
                <span key={item}>{item}</span>
              ))
            ) : (
              <span>无</span>
            )}
          </div>
          <p className={styles.hint}>
            <Image
              aria-hidden="true"
              src="/icons/info-circle.svg"
              alt=""
              width={17}
              height={17}
            />
            硬性约束会由系统自动检查
          </p>

          <label style={{ display: "flex", alignItems: "flex-start", gap: "8px", margin: "14px 0 10px", fontSize: "12px", color: "#475569", cursor: "pointer", lineHeight: 1.4 }}>
            <input
              type="checkbox"
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              style={{ marginTop: "2px", accentColor: "#123f3a", cursor: "pointer" }}
            />
            <span>我已阅读并同意《TravelMind 用户服务协议》与《隐私政策》</span>
          </label>

          <button
            className={styles.submitButton}
            disabled={activeStep !== 4 || submitting || !agreedToTerms}
            type="submit"
          >
            {submitting ? "正在进入规划…" : "开始规划"}
          </button>
          <button
            className={styles.saveDraftButton}
            type="button"
            onClick={saveDraft}
          >
            保存草稿
          </button>
          {draftStatus && (
            <p className={styles.draftStatus} aria-live="polite">
              ✓ {draftStatus}
            </p>
          )}
        </aside>
      </div>
    </form>
  );
}
