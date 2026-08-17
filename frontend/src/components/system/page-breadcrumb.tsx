import Link from "next/link";
import styles from "./page-breadcrumb.module.css";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function PageBreadcrumb({
  items,
  className,
}: {
  items: BreadcrumbItem[];
  className?: string;
}) {
  return (
    <nav aria-label="页面面包屑导航" className={`${styles.breadcrumb} ${className || ""}`}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className={styles.itemWrapper}>
            {item.href && !isLast ? (
              <Link href={item.href} className={styles.link}>
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? styles.current : styles.label}>
                {item.label}
              </span>
            )}
            {!isLast && <span className={styles.separator} aria-hidden="true">/</span>}
          </span>
        );
      })}
    </nav>
  );
}
