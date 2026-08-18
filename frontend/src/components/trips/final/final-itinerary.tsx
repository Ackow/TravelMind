"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { MiniRouteMap } from "./mini-route-map";
import styles from "./final-itinerary.module.css";

interface FinalItineraryProps {
  tripId?: string;
}

interface TimelineActivity {
  id: string;
  time: string;
  category: "flight" | "hotel" | "meal" | "attraction" | "shopping";
  title: string;
  duration: string;
  transitMode?: string;
  cost: string;
}

interface DayPlan {
  dayNumber: number;
  title: string;
  weather: {
    temp: string;
    desc: string;
    icon: string;
  };
  dailyCost: string;
  walking: string;
  activities: TimelineActivity[];
}

const ITINERARY_DAYS: DayPlan[] = [
  {
    dayNumber: 1,
    title: "Day 1 · 浅草与秋叶原",
    weather: { temp: "24-26°C", desc: "晴", icon: "/icons/weather-sunny.svg" },
    dailyCost: "¥1,850",
    walking: "7.2 km",
    activities: [
      {
        id: "d1-1",
        time: "09:00",
        category: "flight",
        title: "抵达成田机场 · 入境与取行李",
        duration: "1h 30m",
        transitMode: "机场快线",
        cost: "¥3,070",
      },
      {
        id: "d1-2",
        time: "11:00",
        category: "hotel",
        title: "入住酒店 · 浅草豪景酒店 (浅草)",
        duration: "1h",
        transitMode: "地铁 35 分钟",
        cost: "¥0",
      },
      {
        id: "d1-3",
        time: "12:30",
        category: "meal",
        title: "午餐 · 上野牛舌",
        duration: "1h",
        transitMode: "步行 10 分钟",
        cost: "¥1,500",
      },
      {
        id: "d1-4",
        time: "14:00",
        category: "attraction",
        title: "浅草寺 · 雷门与仲见世",
        duration: "1h 30m",
        transitMode: "步行 8 分钟",
        cost: "¥0",
      },
      {
        id: "d1-5",
        time: "16:00",
        category: "shopping",
        title: "秋叶原 · 电器街与动漫店",
        duration: "2h",
        transitMode: "地铁 20 分钟",
        cost: "¥0",
      },
      {
        id: "d1-6",
        time: "19:00",
        category: "meal",
        title: "晚餐 · 鸟贵族 (秋叶原店)",
        duration: "1h",
        transitMode: "步行 6 分钟",
        cost: "¥2,500",
      },
    ],
  },
  {
    dayNumber: 2,
    title: "Day 2 · 博物馆与东京站",
    weather: { temp: "18-22°C", desc: "小雨", icon: "/icons/weather-light-rain.svg" },
    dailyCost: "¥2,150",
    walking: "6.2 km",
    activities: [
      {
        id: "d2-1",
        time: "09:30",
        category: "attraction",
        title: "东京国立博物馆",
        duration: "2h",
        transitMode: "地铁 15 分钟",
        cost: "¥1,000",
      },
      {
        id: "d2-2",
        time: "12:00",
        category: "meal",
        title: "午餐 · 上野公园周边定食",
        duration: "1h",
        transitMode: "步行 5 分钟",
        cost: "¥1,200",
      },
      {
        id: "d2-3",
        time: "14:30",
        category: "attraction",
        title: "teamLab Borderless",
        duration: "2h 30m",
        transitMode: "地铁 25 分钟",
        cost: "¥3,800",
      },
      {
        id: "d2-4",
        time: "18:30",
        category: "meal",
        title: "晚餐 · 银座拉面",
        duration: "1h",
        transitMode: "步行 8 分钟",
        cost: "¥950",
      },
    ],
  },
  {
    dayNumber: 3,
    title: "Day 3 · 涩谷与表参道",
    weather: { temp: "19-25°C", desc: "晴", icon: "/icons/weather-sunny.svg" },
    dailyCost: "¥1,900",
    walking: "6.8 km",
    activities: [
      {
        id: "d3-1",
        time: "10:00",
        category: "attraction",
        title: "明治神宫与代代木公园",
        duration: "2h",
        transitMode: "地铁 20 分钟",
        cost: "¥0",
      },
      {
        id: "d3-2",
        time: "12:30",
        category: "meal",
        title: "表参道轻食咖啡",
        duration: "1h",
        transitMode: "步行 10 分钟",
        cost: "¥1,400",
      },
      {
        id: "d3-3",
        time: "14:30",
        category: "shopping",
        title: "涩谷 Shibuya Sky 展望台",
        duration: "2h",
        transitMode: "步行 12 分钟",
        cost: "¥2,200",
      },
      {
        id: "d3-4",
        time: "18:00",
        category: "meal",
        title: "晚餐 · 涩谷居酒屋",
        duration: "1h 30m",
        transitMode: "步行 5 分钟",
        cost: "¥2,800",
      },
    ],
  },
  {
    dayNumber: 4,
    title: "Day 4 · 镰仓一日",
    weather: { temp: "17-23°C", desc: "多云", icon: "/icons/weather-partly-cloudy.svg" },
    dailyCost: "¥1,600",
    walking: "9.1 km",
    activities: [
      {
        id: "d4-1",
        time: "08:30",
        category: "attraction",
        title: "镰仓高校前与江之电巡礼",
        duration: "2h",
        transitMode: "电车 55 分钟",
        cost: "¥1,100",
      },
      {
        id: "d4-2",
        time: "11:30",
        category: "attraction",
        title: "镰仓大佛 · 高德院参拜",
        duration: "1h 30m",
        transitMode: "电车 15 分钟",
        cost: "¥300",
      },
      {
        id: "d4-3",
        time: "13:30",
        category: "meal",
        title: "午餐 · 小町通街头美食",
        duration: "1h",
        transitMode: "步行 10 分钟",
        cost: "¥1,600",
      },
      {
        id: "d4-4",
        time: "16:00",
        category: "attraction",
        title: "江之岛海岸日落漫步",
        duration: "2h",
        transitMode: "电车 20 分钟",
        cost: "¥0",
      },
    ],
  },
  {
    dayNumber: 5,
    title: "Day 5 · 银座返程",
    weather: { temp: "18-24°C", desc: "阴", icon: "/icons/weather-overcast.svg" },
    dailyCost: "¥960",
    walking: "9.3 km",
    activities: [
      {
        id: "d5-1",
        time: "09:00",
        category: "shopping",
        title: "银座百货与伊东屋文具",
        duration: "2h 30m",
        transitMode: "地铁 15 分钟",
        cost: "¥0",
      },
      {
        id: "d5-2",
        time: "12:00",
        category: "meal",
        title: "午餐 · 银座寿司定食",
        duration: "1h",
        transitMode: "步行 5 分钟",
        cost: "¥2,200",
      },
      {
        id: "d5-3",
        time: "14:30",
        category: "flight",
        title: "前往成田机场 · 办理退税与登机",
        duration: "2h",
        transitMode: "机场快线",
        cost: "¥3,070",
      },
    ],
  },
];

export function FinalItinerary({ tripId = "tokyo-5d" }: FinalItineraryProps) {
  const router = useRouter();
  const [expandedDays, setExpandedDays] = useState<number[]>([1]);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<{ [key: string]: boolean }>({
    teamlab: true,
    rain: true,
    iccard: true,
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2600);
  };

  const toggleDay = (dayNumber: number) => {
    if (expandedDays.includes(dayNumber)) {
      setExpandedDays(expandedDays.filter((d) => d !== dayNumber));
    } else {
      setExpandedDays([...expandedDays, dayNumber]);
    }
  };

  const handleShare = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
    }
    showToast("行程公开分享链接已复制到剪贴板");
  };

  const handleExportPdf = () => {
    showToast("准备导出 PDF... 正在生成打印视图");
    setTimeout(() => {
      window.print();
    }, 600);
  };

  const toggleCheck = (key: string) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "flight":
        return "/icons/train.svg";
      case "hotel":
        return "/icons/calendar.svg";
      case "meal":
        return "/icons/meal.svg";
      case "shopping":
        return "/icons/shopping.svg";
      case "attraction":
      default:
        return "/icons/attraction.svg";
    }
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
        {/* Top Header Row with Left Title and Right Action Buttons */}
        <header className={styles.topHeaderRow}>
          <div className={styles.heroLeft}>
            <div className={styles.statusBadge}>
              <span className={styles.statusIcon}>✓</span>
              <span>已确认</span>
            </div>

            <h1 className={styles.heroTitle}>东京 · 5 日旅行计划</h1>

            <p className={styles.heroSubtitle}>
              2026 年 10 月 1 日—10 月 5 日 · 2 位旅行者
            </p>

            <div className={styles.routeRow}>
              <span className={styles.routeText}>南京 → 东京</span>
            </div>

            <div className={styles.tagRow}>
              <span className={styles.tagPill}>动漫</span>
              <span className={styles.tagPill}>美食</span>
              <span className={styles.tagPill}>城市漫步</span>
              <span className={styles.versionPill}>版本 2</span>
            </div>
          </div>

          <div className={styles.heroActions}>
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handleShare}
            >
              <Image
                src="/icons/export.svg"
                alt=""
                width={16}
                height={16}
                className={styles.darkIcon}
              />
              <span>分享链接</span>
            </button>

            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handleExportPdf}
            >
              <Image
                src="/icons/clipboard-list.svg"
                alt=""
                width={16}
                height={16}
                className={styles.darkIcon}
              />
              <span>导出 PDF</span>
            </button>

            <button
              type="button"
              className={styles.primaryBtn}
              onClick={() => router.push(`/trips/${tripId}/history`)}
            >
              查看版本
            </button>
          </div>
        </header>

        {/* Two-Column Main Layout: Left (Stats + Banner + 5 Days) & Right (Summary + Checklist) */}
        <div className={styles.mainGrid}>
          {/* Left Column */}
          <main className={styles.leftCol} aria-label="行程详情">
            {/* 4 Summary Stat Cards */}
            <section className={styles.statsRow} aria-label="行程核心数据">
              <div className={styles.statCard}>
                <Image
                  src="/icons/calendar.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>5 天 4 晚</strong>
              </div>

              <div className={styles.statCard}>
                <Image
                  src="/icons/clipboard-list.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>18 个活动</strong>
              </div>

              <div className={styles.statCard}>
                <Image
                  src="/icons/wallet.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>预计 ¥8,460</strong>
              </div>

              <div className={styles.statCard}>
                <Image
                  src="/icons/walking.svg"
                  alt=""
                  width={22}
                  height={22}
                  className={styles.tealIcon}
                />
                <strong className={styles.statValue}>步行 38.6 km</strong>
              </div>
            </section>

            {/* Validation Statement Banner */}
            <div className={styles.validationBanner}>
              <span className={styles.verifCheckIcon}>✓</span>
              <span className={styles.verifBannerText}>所有硬性约束已通过</span>
            </div>

            {/* 5 Days Accordion */}
            <div className={styles.daysAccordion}>
              {ITINERARY_DAYS.map((day) => {
                const isExpanded = expandedDays.includes(day.dayNumber);

                return (
                  <section
                    key={day.dayNumber}
                    className={`${styles.dayCard} ${
                      isExpanded ? styles.dayCardExpanded : ""
                    }`}
                  >
                    {/* Day Header Row */}
                    <button
                      type="button"
                      className={styles.dayHeader}
                      onClick={() => toggleDay(day.dayNumber)}
                      aria-expanded={isExpanded}
                    >
                      <strong className={styles.dayTitle}>{day.title}</strong>

                      <div className={styles.dayMeta}>
                        <div className={styles.dayWeather}>
                          <Image
                            src={day.weather.icon}
                            alt=""
                            width={18}
                            height={18}
                          />
                          <span>{day.weather.temp} {day.weather.desc}</span>
                        </div>

                        <div className={styles.dayMetaItem}>
                          <Image
                            src="/icons/wallet.svg"
                            alt=""
                            width={16}
                            height={16}
                            className={styles.mutedIcon}
                          />
                          <span>{day.dailyCost}</span>
                        </div>

                        <div className={styles.dayMetaItem}>
                          <Image
                            src="/icons/walking.svg"
                            alt=""
                            width={16}
                            height={16}
                            className={styles.mutedIcon}
                          />
                          <span>{day.walking}</span>
                        </div>

                        <span
                          className={`${styles.dayChevron} ${
                            isExpanded ? styles.dayChevronOpen : ""
                          }`}
                        >
                          {isExpanded ? "⌃" : "⌄"}
                        </span>
                      </div>
                    </button>

                    {/* Timeline Body with Smooth Animated Transition */}
                    <div
                      className={`${styles.timelineCollapseWrapper} ${
                        isExpanded ? styles.timelineCollapseOpen : ""
                      }`}
                    >
                      <div className={styles.timelineCollapseInner}>
                        <div className={styles.timelineBody}>
                          {day.activities.map((act, index) => {
                            const isLast = index === day.activities.length - 1;

                            return (
                              <div key={act.id} className={styles.activityRow}>
                                {/* Left Time & Bullet */}
                                <div className={styles.activityTimeCol}>
                                  <div className={styles.timeNodeWrapper}>
                                    <div className={styles.timeBullet} />
                                    {!isLast && <div className={styles.timeTrack} />}
                                  </div>
                                  <span className={styles.actTime}>{act.time}</span>
                                </div>

                                {/* Category Icon */}
                                <div className={styles.actIconArea}>
                                  <Image
                                    src={getCategoryIcon(act.category)}
                                    alt=""
                                    width={18}
                                    height={18}
                                    className={styles.darkIcon}
                                  />
                                </div>

                                {/* Title */}
                                <div className={styles.actTitleArea}>
                                  <span className={styles.actTitle}>{act.title}</span>
                                </div>

                                {/* Duration */}
                                <div className={styles.actDuration}>
                                  <span>{act.duration}</span>
                                </div>

                                {/* Transit Transition */}
                                <div className={styles.actTransit}>
                                  {act.transitMode && (
                                    <span className={styles.transitBadge}>
                                      <Image
                                        src={act.transitMode.includes("步行") ? "/icons/walking.svg" : "/icons/train.svg"}
                                        alt=""
                                        width={14}
                                        height={14}
                                        className={styles.mutedIcon}
                                      />
                                      {act.transitMode}
                                    </span>
                                  )}
                                </div>

                                {/* Cost */}
                                <div className={styles.actCost}>
                                  <span>{act.cost}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </section>
                );
              })}
            </div>
          </main>

          {/* Right Column: Sticky Summary & Checklist starting at same level as Stats */}
          <aside className={styles.rightCol} aria-label="旅行总览与提醒">
            {/* Card 1: 旅行总览 */}
            <div className={styles.card}>
              <h2 className={styles.sidebarCardTitle}>旅行总览</h2>

              {/* Map Graphic */}
              <MiniRouteMap />

              {/* Budget Progress Bar */}
              <div className={styles.budgetSummaryArea}>
                <div className={styles.budgetMainRow}>
                  <strong className={styles.budgetCurrent}>¥8,460</strong>
                  <span className={styles.budgetLimit}>/ ¥10,000</span>
                  <span className={styles.budgetLeft}>预留 ¥1,540</span>
                </div>

                <div className={styles.progressBarTrack}>
                  <div className={styles.progressBarFill} style={{ width: "85%" }} />
                </div>
                <div className={styles.progressPercentLabel}>85%</div>
              </div>

              {/* Breakdown Bars */}
              <div className={styles.breakdownList}>
                {/* 1. 住宿 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/calendar.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.tealIcon}
                    />
                    <span>住宿</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{ width: "37%", backgroundColor: "#0f766e" }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>¥3,200 (37%)</span>
                </div>

                {/* 2. 餐饮 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/meal.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.emeraldIcon}
                    />
                    <span>餐饮</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{ width: "29%", backgroundColor: "#10b981" }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>¥2,460 (29%)</span>
                </div>

                {/* 3. 交通 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/train.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.blueIcon}
                    />
                    <span>交通</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{ width: "21%", backgroundColor: "#3b82f6" }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>¥1,800 (21%)</span>
                </div>

                {/* 4. 门票与活动 */}
                <div className={styles.breakdownRow}>
                  <div className={styles.breakdownLabelArea}>
                    <Image
                      src="/icons/attraction.svg"
                      alt=""
                      width={15}
                      height={15}
                      className={styles.orangeIcon}
                    />
                    <span>门票与活动</span>
                  </div>
                  <div className={styles.categoryTrack}>
                    <div
                      className={styles.categoryFill}
                      style={{ width: "12%", backgroundColor: "#f97316" }}
                    />
                  </div>
                  <span className={styles.breakdownAmount}>¥1,000 (12%)</span>
                </div>
              </div>
            </div>

            {/* Card 2: 出发前提醒 */}
            <div className={styles.card}>
              <h2 className={styles.sidebarCardTitle}>出发前提醒</h2>

              <div className={styles.checklist}>
                <label className={styles.checkItem}>
                  <input
                    type="checkbox"
                    checked={checklist.teamlab}
                    onChange={() => toggleCheck("teamlab")}
                    className={styles.checkboxInput}
                  />
                  <span className={styles.customCheckCircle}>✓</span>
                  <span className={styles.checkLabel}>预约 teamLab</span>
                </label>

                <label className={styles.checkItem}>
                  <input
                    type="checkbox"
                    checked={checklist.rain}
                    onChange={() => toggleCheck("rain")}
                    className={styles.checkboxInput}
                  />
                  <span className={styles.customCheckCircle}>✓</span>
                  <span className={styles.checkLabel}>准备雨具</span>
                </label>

                <label className={styles.checkItem}>
                  <input
                    type="checkbox"
                    checked={checklist.iccard}
                    onChange={() => toggleCheck("iccard")}
                    className={styles.checkboxInput}
                  />
                  <span className={styles.customCheckCircle}>✓</span>
                  <span className={styles.checkLabel}>确认交通卡</span>
                </label>
              </div>

              {/* Info Block with SVG Icon */}
              <div className={styles.departureInfoBlock}>
                <Image
                  src="/icons/info-circle.svg"
                  alt=""
                  width={16}
                  height={16}
                  className={styles.infoIconFilter}
                />
                <p className={styles.departureInfoText}>
                  天气与开放时间获取于 8 月 13 日，出发前请再次确认
                </p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
