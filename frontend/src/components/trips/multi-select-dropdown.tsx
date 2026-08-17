"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import styles from "./multi-select-dropdown.module.css";

type Option<T extends string> = {
  value: T;
  label: string;
};

type MultiSelectDropdownProps<T extends string> = {
  label: string;
  options: Option<T>[];
  values: T[];
  emptyText?: string;
  onChange: (values: T[]) => void;
};

export function MultiSelectDropdown<T extends string>({
  label,
  options,
  values,
  emptyText = "请选择",
  onChange,
}: MultiSelectDropdownProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const selectedLabels = options
    .filter((option) => values.includes(option.value))
    .map((option) => option.label);

  const openDropdown = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsClosing(false);
    setIsOpen(true);
  }, []);

  const closeDropdown = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsClosing(true);
    timerRef.current = setTimeout(() => {
      setIsOpen(false);
      setIsClosing(false);
      timerRef.current = null;
    }, 180);
  }, []);

  function handleToggle() {
    if (isOpen && !isClosing) {
      closeDropdown();
    } else {
      openDropdown();
    }
  }

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        if (isOpen && !isClosing) {
          closeDropdown();
        }
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen && !isClosing) {
        closeDropdown();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isOpen, isClosing, closeDropdown]);

  function toggleOption(value: T) {
    onChange(
      values.includes(value)
        ? values.filter((current) => current !== value)
        : [...values, value],
    );
  }

  const showMenu = isOpen || isClosing;

  return (
    <div className={styles.field} ref={containerRef}>
      <span className={styles.label}>{label}</span>
      <div className={styles.dropdown}>
        <button
          type="button"
          className={`${styles.trigger} ${isOpen && !isClosing ? styles.triggerOpen : ""}`}
          onClick={handleToggle}
          aria-haspopup="listbox"
          aria-expanded={isOpen && !isClosing}
        >
          <span
            className={
              selectedLabels.length ? styles.value : styles.placeholder
            }
          >
            {selectedLabels.length ? selectedLabels.join("、") : emptyText}
          </span>
          <svg
            className={`${styles.arrow} ${isOpen && !isClosing ? styles.arrowOpen : ""}`}
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {showMenu && (
          <div
            className={`${styles.menu} ${isClosing ? styles.menuClosing : ""}`}
            role="listbox"
          >
            {options.map((option) => (
              <label className={styles.option} key={option.value}>
                <input
                  type="checkbox"
                  checked={values.includes(option.value)}
                  onChange={() => toggleOption(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
