"use client";

import { useEffect } from "react";
import styles from "./conflict-detail-modal.module.css";

export type ConflictType = "budget" | "hours" | "walking";

interface ConflictDetailModalProps {
  type: ConflictType | null;
  onClose: () => void;
  onApplyFix: (fixType: string) => void;
}

export function ConflictDetailModal({
  type,
  onClose,
  onApplyFix,
}: ConflictDetailModalProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    if (type) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [type, onClose]);

  if (!type) return null;

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <header className={styles.header}>
          <div className={styles.headerTitle}>
            <span className={styles.badge}>冲突诊断</span>
            <h3>
              {type === "budget" && "总预算不足分析"}
              {type === "hours" && "必去地点营业时间冲突分析"}
              {type === "walking" && "每日步行上限过低分析"}
            </h3>
          </div>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </header>

        <div className={styles.content}>
          {type === "budget" && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                系统计算了当前东京 5 日游的不可压缩基础花费与必去项目门票，总额超出了您的设定上限：
              </p>
              <div className={styles.breakdownTable}>
                <div className={styles.row}>
                  <span>往返机票 (2人预计)</span>
                  <strong>¥4,800</strong>
                </div>
                <div className={styles.row}>
                  <span>舒适型酒店 (4晚累计)</span>
                  <strong>¥4,000</strong>
                </div>
                <div className={styles.row}>
                  <span>必选景点门票 (吉卜力+迪士尼)</span>
                  <strong>¥1,400</strong>
                </div>
                <div className={styles.row}>
                  <span>基础交通及市内换乘</span>
                  <strong>¥1,000</strong>
                </div>
                <div className={`${styles.row} ${styles.totalRow}`}>
                  <span>预计最低不可压缩总支出</span>
                  <span className={styles.highlightRed}>¥11,200</span>
                </div>
                <div className={`${styles.row} ${styles.limitRow}`}>
                  <span>您设置的预算上限</span>
                  <span className={styles.limitValue}>¥10,000</span>
                </div>
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>将行程预算提高至 ¥11,200 即可保留所有必选地点，或降低住宿标准。</p>
              </div>
            </div>
          )}

          {type === "hours" && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                您标记的必去地点在行程可调度的时间窗口内处于闭馆状态：
              </p>
              <div className={styles.conflictList}>
                <div className={styles.conflictCard}>
                  <div className={styles.conflictCardHeader}>
                    <strong>根津美术馆</strong>
                    <span className={styles.tagClosed}>周三闭馆</span>
                  </div>
                  <p>当前路线唯一可插入时段为：第 3 天 (周三) 下午</p>
                </div>
                <div className={styles.conflictCard}>
                  <div className={styles.conflictCardHeader}>
                    <strong>三鹰之森吉卜力美术馆</strong>
                    <span className={styles.tagClosed}>周三休馆维护</span>
                  </div>
                  <p>原定日程安排于第 3 天，但该日不对外开放</p>
                </div>
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>调整游玩顺序将景点移至周四，或暂时移除其中一个必去地点。</p>
              </div>
            </div>
          )}

          {type === "walking" && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                东京市内游览及大型枢纽站换乘的最低生理步行量超出您的每日上限：
              </p>
              <div className={styles.breakdownTable}>
                <div className={styles.row}>
                  <span>涩谷-原宿-新宿 街区漫步</span>
                  <strong>4.2 km</strong>
                </div>
                <div className={styles.row}>
                  <span>浅草寺与上野公园游览</span>
                  <strong>3.8 km</strong>
                </div>
                <div className={styles.row}>
                  <span>JR/地铁站内换乘必要步行</span>
                  <strong>1.3 km</strong>
                </div>
                <div className={`${styles.row} ${styles.totalRow}`}>
                  <span>单日最低不可避免步行量</span>
                  <span className={styles.highlightRed}>9.3 km</span>
                </div>
                <div className={`${styles.row} ${styles.limitRow}`}>
                  <span>您设置的每日步行上限</span>
                  <span className={styles.limitValue}>5.0 km</span>
                </div>
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>允许其中 1 天步行上限提升至 10 km，或增加出租车点对点接驳预算。</p>
              </div>
            </div>
          )}
        </div>

        <footer className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>
            关闭
          </button>
          <button
            type="button"
            className={styles.applyBtn}
            onClick={() => {
              if (type === "budget") onApplyFix("budget");
              if (type === "hours") onApplyFix("remove_poi");
              if (type === "walking") onApplyFix("walking");
              onClose();
            }}
          >
            采用此调整方案
          </button>
        </footer>
      </div>
    </div>
  );
}
