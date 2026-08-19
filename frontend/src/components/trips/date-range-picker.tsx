"use client";

import { useEffect, useRef, useState } from "react";
import { DayPicker, type DateRange } from "@daypicker/react";
import { zhCN } from "@daypicker/react/locale";
import Image from "next/image";

import styles from "./date-range-picker.module.css";

type DateRangePickerProps = {
  startDate: string;
  endDate: string;
  onChange: (startDate: string, endDate: string) => void;
};

function fromIso(value: string): Date | undefined {
  if (!value || typeof value !== "string" || !value.includes("-")) {
    return undefined;
  }
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return undefined;
  const date = new Date(year, month - 1, day);
  return isNaN(date.getTime()) ? undefined : date;
}

function toIso(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function formatDisplay(value: string, placeholder = "请选择日期"): string {
  const parsed = fromIso(value);
  if (!parsed) return placeholder;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}

function getRangeDayCount(from?: Date, to?: Date): number {
  if (!from || !to) return 0;
  const start = new Date(from.getFullYear(), from.getMonth(), from.getDate());
  const end = new Date(to.getFullYear(), to.getMonth(), to.getDate());
  const ms = end.getTime() - start.getTime();
  return Math.max(1, Math.round(ms / 86_400_000) + 1);
}

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
}: DateRangePickerProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const fromDate = fromIso(startDate);
  const toDate = fromIso(endDate);
  const selected: DateRange | undefined =
    fromDate && toDate
      ? {
          from: fromDate,
          to: toDate,
        }
      : undefined;

  const [draft, setDraft] = useState<DateRange | undefined>(selected);
  const [feedback, setFeedback] = useState<string | null>(null);

  // 同步外部 props
  useEffect(() => {
    if (fromDate && toDate) {
      setDraft({ from: fromDate, to: toDate });
    }
  }, [startDate, endDate]);

  // 控制动画退场
  const [isClosing, setIsClosing] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  function closePickerWithAnimation() {
    setIsClosing(true);
    timerRef.current = setTimeout(() => {
      detailsRef.current?.removeAttribute("open");
      setIsClosing(false);
    }, 200);
  }

  useEffect(() => {
    function closeWhenClickingOutside(event: PointerEvent) {
      const picker = detailsRef.current;
      if (picker && !picker.contains(event.target as Node)) {
        picker.removeAttribute("open");
      }
    }

    function closeWhenPressingEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closePickerWithAnimation();
      }
    }

    document.addEventListener("pointerdown", closeWhenClickingOutside);
    document.addEventListener("keydown", closeWhenPressingEscape);
    return () => {
      document.removeEventListener("pointerdown", closeWhenClickingOutside);
      document.removeEventListener("keydown", closeWhenPressingEscape);
    };
  }, []);

  function handleSelect(
    range: DateRange | undefined,
    triggerDate?: Date,
  ) {
    const clicked = triggerDate || range?.from;
    if (!clicked) {
      setDraft(undefined);
      setFeedback("请点击出发日期");
      return;
    }

    // 1. 如果当前已有完整区间 (已选好 from 和 to)，再次点击任何一天立即作为【新出发日】重新开始
    if (draft?.from && draft?.to) {
      setDraft({ from: clicked, to: undefined });
      setFeedback(`已选择出发日（${formatDisplay(toIso(clicked))}），请点击返回日（3～7 天）`);
      return;
    }

    // 2. 如果当前仅有出发日，用户正在选择返回日：
    if (draft?.from && !draft?.to) {
      if (clicked < draft.from) {
        // 用户点击了更早的日期，则将更早日期更新为新的出发日
        setDraft({ from: clicked, to: undefined });
        setFeedback(`已更新出发日（${formatDisplay(toIso(clicked))}），请点击返回日（3～7 天）`);
        return;
      }

      // 用户正常选择了结束日
      const days = getRangeDayCount(draft.from, clicked);
      const newRange = { from: draft.from, to: clicked };
      setDraft(newRange);

      if (days < 3) {
        setFeedback(`已选 ${days} 天：MVP 阶段行程至少需要 3 天`);
        return;
      }
      if (days > 7) {
        setFeedback(`已选 ${days} 天：MVP 阶段最多支持 7 天行程`);
        return;
      }

      setFeedback(`✓ 已选 ${days} 天 ${days - 1} 晚（符合要求）`);
      onChange(toIso(draft.from), toIso(clicked));
      setTimeout(() => {
        closePickerWithAnimation();
      }, 250);
      return;
    }

    // 3. 初次未选择时的单次点击
    setDraft({ from: clicked, to: undefined });
    setFeedback(`已选择出发日（${formatDisplay(toIso(clicked))}），请点击返回日（3～7 天）`);
  }

  function applyQuickPreset(days: number) {
    const base = draft?.from || new Date();
    const start = new Date(base.getFullYear(), base.getMonth(), base.getDate());
    const end = addDays(start, days - 1);
    setDraft({ from: start, to: end });
    setFeedback(`✓ 已选 ${days} 天 ${days - 1} 晚`);
    onChange(toIso(start), toIso(end));
    setTimeout(() => {
      closePickerWithAnimation();
    }, 200);
  }

  const selectedDays = getRangeDayCount(draft?.from, draft?.to);
  const isRangeValid = selectedDays >= 3 && selectedDays <= 7;

  return (
    <label className={styles.field}>
      出行日期（MVP 支持 3 ~ 7 天）
      <details className={styles.picker} ref={detailsRef}>
        <summary>
          <Image
            aria-hidden="true"
            src="/icons/calendar.svg"
            alt=""
            width={20}
            height={20}
          />
          <span>{formatDisplay(startDate, "出发日期")}</span>
          <b aria-hidden="true">→</b>
          <span>{formatDisplay(endDate, "返回日期")}</span>
        </summary>
        <div className={`${styles.popover} ${isClosing ? styles.popoverClosing : ""}`}>
          <div className={styles.popoverHeading}>
            <strong>选择出行日期</strong>
            <small style={{ color: isRangeValid ? "#10b981" : "#e11d48", fontWeight: 600 }}>
              {feedback || "请选择 3 ~ 7 天出行区间"}
            </small>
          </div>

          {/* 快捷天数标签 */}
          <div style={{ display: "flex", gap: "6px", marginBottom: "10px", alignItems: "center" }}>
            <span style={{ fontSize: "11px", color: "#64748b" }}>快捷预设：</span>
            {[3, 4, 5, 7].map((d) => (
              <button
                key={d}
                type="button"
                style={{
                  background: selectedDays === d ? "#123f3a" : "#f1f5f9",
                  color: selectedDays === d ? "#ffffff" : "#334155",
                  border: "1px solid #e2e8f0",
                  padding: "2px 8px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
                onClick={() => applyQuickPreset(d)}
              >
                {d}天
              </button>
            ))}
          </div>

          <DayPicker
            mode="range"
            locale={zhCN}
            selected={draft}
            onSelect={(range, selectedDay) => handleSelect(range, selectedDay)}
            disabled={{ before: new Date(new Date().setHours(0, 0, 0, 0)) }}
            defaultMonth={draft?.from ?? new Date()}
            numberOfMonths={1}
            showOutsideDays
          />

          <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "#64748b" }}>
            <span>
              {draft?.from && draft?.to
                ? `已选天数：${selectedDays} 天 ${selectedDays - 1} 晚`
                : draft?.from
                ? `已选出发日 (${formatDisplay(toIso(draft.from))})，请选返回日`
                : "请在日历中点击出发日"}
            </span>
            {draft?.from && draft?.to && isRangeValid && (
              <button
                type="button"
                style={{
                  background: "#123f3a",
                  color: "#fff",
                  border: "none",
                  padding: "4px 12px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
                onClick={() => {
                  if (draft.from && draft.to) {
                    onChange(toIso(draft.from), toIso(draft.to));
                    closePickerWithAnimation();
                  }
                }}
              >
                确认使用
              </button>
            )}
          </div>
        </div>
      </details>
    </label>
  );
}
