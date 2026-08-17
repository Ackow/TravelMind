import Image from "next/image";
import Link from "next/link";

import styles from "../support-page.module.css";

const IDEAS = [
  ["东京城市探索", "动漫、美食与城市漫步", "/icons/map-pin.svg"],
  ["博物馆主题旅行", "用开放时间组织室内行程", "/icons/museum.svg"],
  ["轻松低步行方案", "优先公共交通并减少换乘", "/icons/train.svg"],
] as const;

export default function ExplorePage() {
  return (
    <main className={styles.page}>
      <p className={styles.eyebrow}>灵感库</p>
      <h1>探索旅行方式</h1>
      <p className={styles.lead}>
        从一个主题开始，再进入创建页完善日期、预算和约束。
      </p>
      <section className={styles.cardGrid}>
        {IDEAS.map(([title, description, icon]) => (
          <Link href="/trips/new" key={title}>
            <Image src={icon} width={32} height={32} alt="" />
            <h2>{title}</h2>
            <p>{description}</p>
            <span>以此创建旅行 →</span>
          </Link>
        ))}
      </section>
    </main>
  );
}
