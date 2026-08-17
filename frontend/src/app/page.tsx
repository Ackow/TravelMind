import Image from "next/image";
import Link from "next/link";

import styles from "./page.module.css";

const capabilities = [
  {
    icon: "live",
    title: "实时信息",
    description: "把天气、开放时间和交通变化纳入规划。",
  },
  {
    icon: "check",
    title: "约束检查",
    description: "预算、步行距离与时间安排都可验证。",
  },
  {
    icon: "refresh",
    title: "动态调整",
    description: "提出新要求后，保留理由地生成新版本。",
  },
];

export default function HomePage() {
  return (
    <main className={styles.page}>
      <section className={styles.pageHeading}>
        <div>
          <p className={styles.eyebrow}>旅行工作台</p>
          <h1>我的旅行</h1>
          <p>规划、调整并保存你的每一次旅行。</p>
        </div>
        <Link className={styles.primaryButton} href="/trips/new">
          <span aria-hidden="true">＋</span>
          创建新旅行
        </Link>
      </section>

      <section className={styles.workspace}>
        <article className={styles.emptyState}>
          <Image
            className={styles.routeIllustration}
            src="/homepage.png"
            alt=""
            width={1774}
            height={887}
            priority
          />
          <p className={styles.emptyKicker}>从一个清晰的需求开始</p>
          <h2>还没有旅行计划</h2>
          <p>填写目的地、日期和偏好，TravelMind 会为你构建可调整的行程。</p>
          <Link className={styles.primaryButton} href="/trips/new">
            创建第一段旅行
          </Link>
        </article>

        <aside className={styles.capabilityPanel}>
          <div className={styles.capabilityList}>
            {capabilities.map((capability) => (
              <article className={styles.capabilityItem} key={capability.title}>
                <span className={styles.capabilityIcon} aria-hidden="true">
                  {capability.icon === "live" && (
                    <Image
                      src="/icons/capability-weather.svg"
                      alt=""
                      width={64}
                      height={64}
                    />
                  )}
                  {capability.icon === "check" && (
                    <Image
                      src="/icons/clipboard-check.svg"
                      alt=""
                      width={64}
                      height={64}
                    />
                  )}
                  {capability.icon === "refresh" && (
                    <Image
                      src="/icons/adjustment-sliders.svg"
                      alt=""
                      width={64}
                      height={64}
                    />
                  )}
                </span>
                <div>
                  <h2>{capability.title}</h2>
                  <p>{capability.description}</p>
                </div>
              </article>
            ))}
          </div>
        </aside>
      </section>

      <section className={styles.processCard} aria-label="TravelMind 规划流程">
        <h2>规划流程</h2>
        <ol className={styles.processSteps}>
          <li className={styles.processStep}>
            <span>1</span>
            <Image
              src="/icons/clipboard-list.svg"
              alt=""
              width={32}
              height={32}
            />
            <strong>填写需求</strong>
          </li>
          <li className={styles.flowArrow} aria-hidden="true">
            <span />
            <b>›</b>
          </li>
          <li className={styles.processStep}>
            <span>2</span>
            <Image src="/icons/search.svg" alt="" width={32} height={32} />
            <strong>查询信息</strong>
          </li>
          <li className={styles.flowArrow} aria-hidden="true">
            <span />
            <b>›</b>
          </li>
          <li className={styles.processStep}>
            <span>3</span>
            <Image
              src="/icons/shield-check.svg"
              alt=""
              width={32}
              height={32}
            />
            <strong>检查冲突</strong>
          </li>
          <li className={styles.flowArrow} aria-hidden="true">
            <span />
            <b>›</b>
          </li>
          <li className={styles.processStep}>
            <span>4</span>
            <Image src="/icons/edit-square.svg" alt="" width={32} height={32} />
            <strong>审阅调整</strong>
          </li>
        </ol>
      </section>
    </main>
  );
}
