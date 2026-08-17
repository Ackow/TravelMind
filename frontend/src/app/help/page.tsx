import Link from "next/link";

import styles from "../support-page.module.css";

export default function HelpPage() {
  return (
    <main className={styles.page}>
      <p className={styles.eyebrow}>使用帮助</p>
      <h1>TravelMind 如何工作</h1>
      <p className={styles.lead}>
        每次规划都从明确需求开始，并保留可审阅的版本记录。
      </p>
      <section className={styles.helpGrid}>
        <article id="settings">
          <b>01</b>
          <h2>填写需求</h2>
          <p>设置目的地、日期、预算、兴趣与步行上限。</p>
        </article>
        <article>
          <b>02</b>
          <h2>生成计划</h2>
          <p>系统查询固定事实并检查时间、预算和交通约束。</p>
        </article>
        <article>
          <b>03</b>
          <h2>审阅调整</h2>
          <p>通过 Agent 对话或手动参数生成新的计划版本。</p>
        </article>
        <article id="about">
          <b>04</b>
          <h2>保留历史</h2>
          <p>旧计划不会被覆盖，新版本会记录父版本关系。</p>
        </article>
      </section>
      <Link className={styles.primaryAction} href="/trips/new">
        开始创建旅行
      </Link>
    </main>
  );
}
