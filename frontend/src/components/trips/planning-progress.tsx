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
    title: "查询天气",
    detail: "已获得 5 天天气数据",
    icon: "/icons/capability-weather.svg",
  },
  {
    title: "搜索景点",
    detail: "筛选出 18 个候选地点",
    icon: "/icons/search.svg",
  },
  {
    title: "计算地点间路线",
    detail: "正在计算 18 个地点的交通矩阵",
    icon: "/icons/train.svg",
  },
  {
    title: "生成候选行程",
    detail: "按区域与开放时间组合日程",
    icon: "/icons/map-pin.svg",
  },
  {
    title: "检查预算与时间",
    detail: "验证预算、步行和营业时间",
    icon: "/icons/shield-check.svg",
  },
  {
    title: "准备草案",
    detail: "正在整理可审阅的旅行计划",
    icon: "/icons/edit-square.svg",
  },
];

const EVENT_NAMES = [
  "System",
  "Weather Tool",
  "POI Tool",
  "Route Tool",
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
        <Link href={`/trips/${tripId}`}>返回旅行详情</Link>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <div>
          <PageBreadcrumb
            items={[
              { label: "我的旅行", href: "/" },
              { label: `${trip?.destination ?? "东京"} 5 日游`, href: `/trips/${tripId}` },
              { label: "正在规划" },
            ]}
          />
          <h1>正在规划你的{trip?.destination ?? "东京"}之旅</h1>
          <p>TravelMind 正在查询事实、生成候选方案并检查约束</p>
        </div>
        <div className={styles.progressActions}>
          <div
            className={styles.progressRing}
            style={
              { "--progress": `${progress * 3.6}deg` } as React.CSSProperties
            }
          >
            <span>{progress}%</span>
          </div>
          <button type="button" onClick={() => router.push(`/trips/${tripId}`)}>
            取消规划
          </button>
        </div>
      </header>

      <section className={styles.layout}>
        <section className={styles.progressCard}>
          <h2>规划进度</h2>
          <ol className={styles.steps}>
            {STEPS.map((step, index) => {
              const complete = index < activeStep || activeStep >= STEPS.length;
              const active = index === activeStep && activeStep < STEPS.length;
              return (
                <li
                  className={
                    active
                      ? styles.activeStep
                      : complete
                        ? styles.completeStep
                        : styles.pendingStep
                  }
                  key={step.title}
                >
                  <span className={styles.stepState}>
                    {complete ? "✓" : index + 1}
                  </span>
                  <Image src={step.icon} width={21} height={21} alt="" />
                  <strong>{step.title}</strong>
                  <p>{step.detail}</p>
                </li>
              );
            })}
          </ol>

          <div className={styles.events}>
            <h3>实时事件</h3>
            {eventRows.map((step, index) => (
              <div key={step.title}>
                <time>10:{31 + index}</time>
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
              <span>{trip?.destination ?? "东京"}</span>
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
                预算 {money(trip?.constraints.total_budget.amount ?? 1000000)}
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
                src="/icons/weather-light-rain.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>Day 2 降雨概率 75%</span>
            </div>
            <div className={styles.warning}>
              <Image
                src="/icons/warning-triangle.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>镰仓户外安排可能需要调整</span>
            </div>
            <div className={styles.info}>
              <Image
                src="/icons/info-circle.svg"
                width={28}
                height={28}
                alt=""
              />
              <span>完成约束检查后会自动给出替代方案</span>
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
                候选地点<strong>18</strong>
              </span>
            </div>
            <div>
              <Image src="/icons/clock.svg" width={31} height={31} alt="" />
              <span>
                已用时间<strong>{Math.min(42, (activeStep + 1) * 6)}s</strong>
              </span>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
