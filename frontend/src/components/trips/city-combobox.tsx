"use client";

import { useEffect, useId, useState } from "react";
import Image from "next/image";

import styles from "./city-combobox.module.css";

export type CityOption = {
  id: string;
  name: string;
  label: string;
  countryCode: string;
  stateCode: string;
  timezone: string | null;
};

type CityComboboxProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSelect?: (city: CityOption) => void;
};

export function CityCombobox({
  label,
  value,
  onChange,
  onSelect,
}: CityComboboxProps) {
  const listId = useId();
  const [options, setOptions] = useState<CityOption[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (value.trim().length < 2 || !open) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `/api/cities?q=${encodeURIComponent(value.trim())}`,
          { signal: controller.signal },
        );
        const data = (await response.json()) as { cities: CityOption[] };
        setOptions(data.cities);
      } catch {
        if (!controller.signal.aborted) setOptions([]);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, value]);

  return (
    <label className={styles.field}>
      {label}
      <span className={styles.control}>
        <Image
          aria-hidden="true"
          src="/icons/search.svg"
          alt=""
          width={20}
          height={20}
        />
        <input
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-expanded={open}
          role="combobox"
          required
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setOptions([]);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          placeholder="输入城市名称搜索"
        />
        {open && value.trim().length >= 2 && (
          <span className={styles.menu} id={listId} role="listbox">
            {loading && <span className={styles.status}>正在查询城市…</span>}
            {!loading && options.length === 0 && (
              <span className={styles.status}>没有匹配结果，请换个关键词</span>
            )}
            {options.map((city) => (
              <button
                key={city.id}
                aria-selected="false"
                role="option"
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(city.name);
                  onSelect?.(city);
                  setOpen(false);
                }}
              >
                <strong>{city.name}</strong>
                <small>{city.label}</small>
              </button>
            ))}
          </span>
        )}
      </span>
    </label>
  );
}
