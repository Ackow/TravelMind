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

function fromIso(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toIso(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDisplay(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(fromIso(value));
}

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
}: DateRangePickerProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const selected: DateRange = {
    from: fromIso(startDate),
    to: fromIso(endDate),
  };
  const [draft, setDraft] = useState<DateRange | undefined>(selected);

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

  function handleSelect(range: DateRange | undefined) {
    if (!range?.from) return;
    setDraft(range);
    if (range.to) {
      onChange(toIso(range.from), toIso(range.to));
      closePickerWithAnimation();
    }
  }

  return (
    <label className={styles.field}>
      出行日期
      <details className={styles.picker} ref={detailsRef}>
        <summary>
          <Image
            aria-hidden="true"
            src="/icons/calendar.svg"
            alt=""
            width={20}
            height={20}
          />
          <span>{formatDisplay(startDate)}</span>
          <b aria-hidden="true">→</b>
          <span>{formatDisplay(endDate)}</span>
        </summary>
        <div className={`${styles.popover} ${isClosing ? styles.popoverClosing : ""}`}>
          <div className={styles.popoverHeading}>
            <strong>选择出行日期</strong>
            <small>先选择出发日，再选择返回日</small>
          </div>
          <DayPicker
            mode="range"
            locale={zhCN}
            selected={draft}
            onSelect={handleSelect}
            defaultMonth={selected.from}
            numberOfMonths={1}
            resetOnSelect
            showOutsideDays
          />
        </div>
      </details>
    </label>
  );
}
