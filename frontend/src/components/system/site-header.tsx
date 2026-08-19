"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import styles from "@/app/layout.module.css";

const NAV_ITEMS = [
  { href: "/", label: "我的旅行" },
  { href: "/trips/history", label: "历史计划" },
  { href: "/explore", label: "探索" },
  { href: "/help", label: "帮助" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const menuRef = useRef<HTMLDivElement>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [unread, setUnread] = useState(2);

  useEffect(() => {
    function closeMenus(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setNotificationsOpen(false);
        setProfileOpen(false);
      }
    }

    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
        setProfileOpen(false);
      }
    }

    document.addEventListener("pointerdown", closeMenus);
    document.addEventListener("keydown", closeWithEscape);
    return () => {
      document.removeEventListener("pointerdown", closeMenus);
      document.removeEventListener("keydown", closeWithEscape);
    };
  }, []);

  return (
    <header className={styles.header}>
      <nav className={styles.nav} aria-label="主导航">
        <Link className={styles.brand} href="/">
          <span className={styles.brandMark} aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="12" stroke="currentColor" strokeWidth="2" />
              <path d="M14 5 L17.5 14 L14 16 L10.5 14 Z" fill="currentColor" />
              <path d="M14 23 L10.5 14 L14 16 L17.5 14 Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
          <span>TravelMind</span>
        </Link>
        <div className={styles.links}>
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/trips/history"
                ? pathname.startsWith("/trips/history")
                : item.href === "/"
                ? pathname === "/" || (pathname.startsWith("/trips") && !pathname.startsWith("/trips/history"))
                : pathname.startsWith(item.href);
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={active ? styles.activeLink : undefined}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
        <div className={styles.actions} ref={menuRef}>
          <div className={styles.menuAnchor}>
            <button
              aria-expanded={notificationsOpen}
              aria-label="查看通知"
              className={styles.notification}
              onClick={() => {
                setNotificationsOpen((current) => !current);
                setProfileOpen(false);
              }}
              type="button"
            >
              <Image
                aria-hidden="true"
                src="/icons/notification-bell.svg"
                alt=""
                width={22}
                height={22}
              />
            </button>
            {notificationsOpen && (
              <section
                className={styles.notificationMenu}
                aria-label="通知列表"
              >
                <header>
                  <strong>通知</strong>
                  <button onClick={() => setUnread(0)} type="button">
                    全部已读
                  </button>
                </header>
                <div className={unread > 0 ? styles.unreadItem : undefined}>
                  <span>计划检查完成</span>
                  <p>旅行计划草案已通过硬性约束检查。</p>
                </div>
                <div className={unread > 0 ? styles.unreadItem : undefined}>
                  <span>天气信息已更新</span>
                  <p>系统会在下一次规划时采用最新天气。</p>
                </div>
              </section>
            )}
          </div>
          <div className={styles.menuAnchor}>
            <button
              aria-expanded={profileOpen}
              aria-label="打开用户菜单"
              className={styles.avatar}
              onClick={() => {
                setProfileOpen((current) => !current);
                setNotificationsOpen(false);
              }}
              type="button"
            >
              M
            </button>
            {profileOpen && (
              <div className={styles.profileMenu}>
                <strong>旅行者</strong>
                <small>本地账户</small>
                <Link
                  href="/help#settings"
                  onClick={() => setProfileOpen(false)}
                >
                  偏好设置
                </Link>
                <Link href="/help#about" onClick={() => setProfileOpen(false)}>
                  关于 TravelMind
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
