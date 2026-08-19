"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getTrip, startPlanning, type TripResponse } from "@/lib/api/trips";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
import styles from "./planning-progress.module.css";

const STEPS = [
  {
    title: "解析旅行需求",
    detail: "已整理出日期、预算与偏好约束",
    icon: "/icons/clipboard-check.svg",
  },
  {
    title: "查询天气与环境",
    detail: "获取出行期间天气与降水概率",
    icon: "/icons/capability-weather.svg",
  },
  {
    title: "检索候选景点与体验",
    detail: "筛选出高匹配度景点与特色美食",
    icon: "/icons/search.svg",
  },
  {
    title: "计算地点间通行路线",
    detail: "正在构建交通时间与换乘矩阵",
    icon: "/icons/train.svg",
  },
  {
    title: "生成候选行程排期",
    detail: "按区域与开放时间组合每日日程",
    icon: "/icons/map-pin.svg",
  },
  {
    title: "硬性约束校验与评估",
    detail: "验证预算、单日步行上限与营业时间",
    icon: "/icons/shield-check.svg",
  },
  {
    title: "生成行程方案",
    detail: "正在整理可审阅的旅行计划草案",
    icon: "/icons/edit-square.svg",
  },
];

const EVENT_NAMES = [
  "System",
  "Weather Tool",
  "POI Tool",
  "Route Matrix",
  "Planner",
  "Rule Engine",
  "System",
];

function money(amount: number) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

export function PlanningProgress({ tripId }: { tripId: string }) {
  const router = useRouter();
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];

    async function run() {
      try {
        const loadedTrip = await getTrip(tripId);
        if (cancelled) return;
        setTrip(loadedTrip);

        const planningPromise = startPlanning(tripId);
        STEPS.slice(1).forEach((_, index) => {
          timers.push(
            setTimeout(
              () => {
                if (!cancelled) setActiveStep(index + 1);
              },
              (index + 1) * 720,
            ),
          );
        });

        await Promise.all([
          planningPromise,
          new Promise((resolve) => timers.push(setTimeout(resolve, 7 * 720))),
        ]);
        if (cancelled) return;
        setActiveStep(STEPS.length);
        timers.push(setTimeout(() => router.replace(`/trips/${tripId}`), 650));
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof Error ? caught.message : "规划失败，请稍后重试",
          );
        }
      }
    }

    void run();
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [router, tripId]);

  const progress =
    activeStep >= STEPS.length ? 100 : Math.min(94, 12 + activeStep * 14);
  const interests = trip?.preferences.interests.slice(0, 3) ?? [];
  const eventRows = useMemo(
    () => STEPS.slice(0, Math.min(activeStep + 1, 4)),
    [activeStep],
  );

  if (error) {
    return (
      <main className={styles.errorState}>
        <h1>规划暂时中断</h1>
        <p>{error}</p>
        <div>
          <button onClick={() => window.location.reload()} type="button">
            重新尝试
          </button>
          <Link href="/">返回首页</Link>
        </div>
      </main>
    );
  }

  const destination = trip?.destination || "目的地";

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <PageBreadcrumb
          items={[
            { label: "我的旅行", href: "/" },
            { label: `${trip?.origin ?? "出发地"} → ${destination}` },
            { label: "正在规划" },
          ]}
        />
        <h1>AI 正在为你规划行程...</h1>
        <p>我们正在查询真实数据并验证约束，这通常需要 5–15 秒</p>
      </header>

      <div className={styles.progressBar}>
        <div
          className={styles.progressFill}
          style={{ width: `${progress}%` }}
        />
      </div>

      <section className={styles.layout}>
        <section className={styles.mainContent}>
          <ol className={styles.stepList}>
            {STEPS.map((step, index) => {
              const done = activeStep > index;
              const current = activeStep === index;
              return (
                <li
                  className={`${styles.stepItem} ${
                    done ? styles.stepDone : current ? styles.stepCurrent : ""
                  }`}
                  key={step.title}
                >
                  <span className={styles.stepNumber}>
                    {done ? (
                      <svg
                        fill="none"
                        height="13"
                        stroke="currentColor"
                        strokeWidth="3"
                        viewBox="0 0 24 24"
                        width="13"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </span>
                  <div>
                    <strong>{step.title}</strong>
                    <p>{step.detail}</p>
                  </div>
                  {current && (
                    <span className={styles.pulseDot} aria-hidden="true" />
                  )}
                </li>
              );
            })}
          </ol>

          <div className={styles.terminal}>
            <header>
              <span />
              <span />
              <span />
              <strong>实时数据检索与约束校验流水</strong>
            </header>
            {eventRows.map((step, index) => (
              <div key={step.title} className={styles.logRow}>
                <time>
                  {new Date(Date.now() - (4 - index) * 1200).toLocaleTimeString(
                    "zh-CN",
                    {
                      hour12: false,
                    },
                  )}
                </time>
                <Image src={step.icon} width={19} height={19} alt="" />
                <span>{EVENT_NAMES[index]}</span>
                <p>{step.detail.replace("正在", "")}</p>
              </div>
            ))}
          </div>
        </section>

        <aside className={styles.sidebar}>
          <section className={styles.tripSummary}>
            <h2>旅行摘要</h2>
            <div>
              <Image src="/icons/map-pin.svg" width={21} height={21} alt="" />
              <span>{destination}</span>
            </div>
            <div>
              <Image src="/icons/calendar.svg" width={21} height={21} alt="" />
              <span>
                {trip?.date_range.start_date ?? "2026/10/01"}—
                {trip?.date_range.end_date ?? "2026/10/05"}
              </span>
            </div>
            <div>
              <Image src="/icons/user.svg" width={21} height={21} alt="" />
              <span>{trip?.travelers ?? 2} 人</span>
            </div>
            <div>
              <Image src="/icons/wallet.svg" width={21} height={21} alt="" />
              <span>
                预算 {money(trip?.constraints.total_budget.amount ?? 800000)}
              </span>
            </div>
            <strong>偏好</strong>
            <p>
              {interests.map((item) => (
                <i key={item.value}>{item.value}</i>
              ))}
            </p>
          </section>

          <section className={styles.findings}>
            <h2>当前发现</h2>
            <div>
              <Image
                src="/icons/weather-sunny.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>已获取 {destination} 实时天气与开放时间</span>
            </div>
            <div className={styles.info}>
              <Image
                src="/icons/shield-check.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>正在校验预算限额与单日步行负荷</span>
            </div>
            <div className={styles.info}>
              <Image
                src="/icons/info-circle.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>完成约束检查后会自动生成结构化方案</span>
            </div>
          </section>

          <section className={styles.metrics}>
            <div>
              <Image src="/icons/wrench.svg" width={31} height={31} alt="" />
              <span>
                工具调用<strong>{Math.min(7, activeStep + 1)}</strong>
              </span>
            </div>
            <div>
              <Image src="/icons/map-pin.svg" width={31} height={31} alt="" />
              <span>
                目标城市<strong>{destination}</strong>
              </span>
            </div>
            <div>
              <Image src="/icons/clock.svg" width={31} height={31} alt="" />
              <span>
                已用时间<strong>{Math.min(42, (activeStep + 1) * 3)}s</strong>
              </span>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
