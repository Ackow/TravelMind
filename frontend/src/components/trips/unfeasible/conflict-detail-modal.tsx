"use client";

import { useEffect } from "react";
import styles from "./conflict-detail-modal.module.css";

export type ConflictType = "budget" | "hours" | "walking" | string;

export interface ViolationDetail {
  code: string;
  message: string;
  actual?: Record<string, unknown> | null;
  expected?: Record<string, unknown> | null;
  repair_hint?: string | null;
}

interface ConflictDetailModalProps {
  type: ConflictType | null;
  violation?: ViolationDetail | null;
  onClose: () => void;
  onApplyFix: (fixType: string) => void;
}

export function ConflictDetailModal({
  type,
  violation,
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

  const actualData = violation?.actual || {};
  const isBudget = type === "budget" || violation?.code === "BUDGET_EXCEEDED";
  const isHours = type === "hours" || violation?.code === "PLACE_CLOSED";
  const isWalking = type === "walking" || violation?.code === "MAX_WALKING_EXCEEDED";

  const breakdownList = (actualData.breakdown as Array<{ category?: string; segment?: string; amount?: number; meters?: number }>) || [];
  const closedPlaces = (actualData.closed_places as Array<{ name: string; reason: string }>) || [];

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <header className={styles.header}>
          <div className={styles.headerTitle}>
            <span className={styles.badge}>冲突诊断</span>
            <h3>
              {isBudget && "总预算不足分析"}
              {isHours && "必去地点营业时间冲突分析"}
              {isWalking && "每日步行上限过低分析"}
              {!isBudget && !isHours && !isWalking && "约束冲突诊断详情"}
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
          {isBudget && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                {violation?.message || "系统计算了当前旅行规划的不可压缩基础花费与必去项目门票，总额超出了您的设定上限："}
              </p>
              <div className={styles.breakdownTable}>
                {breakdownList.length > 0 ? (
                  breakdownList.map((item, idx) => (
                    <div key={idx} className={styles.row}>
                      <span>{item.category || "支出项"}</span>
                      <strong>¥{((item.amount ?? 0) / 100).toLocaleString()}</strong>
                    </div>
                  ))
                ) : (
                  <>
                    <div className={styles.row}>
                      <span>往返大交通 (2人预计)</span>
                      <strong>¥4,800</strong>
                    </div>
                    <div className={styles.row}>
                      <span>舒适型酒店 (累计)</span>
                      <strong>¥4,000</strong>
                    </div>
                    <div className={styles.row}>
                      <span>必选景点门票与体验</span>
                      <strong>¥1,400</strong>
                    </div>
                    <div className={styles.row}>
                      <span>基础交通及市内换乘</span>
                      <strong>¥1,000</strong>
                    </div>
                  </>
                )}
                <div className={`${styles.row} ${styles.totalRow}`}>
                  <span>预计最低不可压缩总支出</span>
                  <span className={styles.highlightRed}>
                    ¥{actualData.estimated_amount ? ((actualData.estimated_amount as number) / 100).toLocaleString() : "11,200"}
                  </span>
                </div>
                <div className={`${styles.row} ${styles.limitRow}`}>
                  <span>您设置的预算上限</span>
                  <span className={styles.limitValue}>
                    ¥{actualData.limit_amount ? ((actualData.limit_amount as number) / 100).toLocaleString() : "10,000"}
                  </span>
                </div>
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>{violation?.repair_hint || "将行程预算提高至 ¥11,200 即可保留所有必选地点，或降低住宿标准。"}</p>
              </div>
            </div>
          )}

          {isHours && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                {violation?.message || "您指定了必去场馆，但在当前出行日期与调度窗口内存在闭馆冲突："}
              </p>
              <div className={styles.breakdownTable}>
                {closedPlaces.length > 0 ? (
                  closedPlaces.map((place, idx) => (
                    <div key={idx} className={styles.row}>
                      <span>{place.name}</span>
                      <span className={styles.highlightRed}>{place.reason}</span>
                    </div>
                  ))
                ) : (
                  <>
                    <div className={styles.row}>
                      <span>文博美术馆</span>
                      <span className={styles.highlightRed}>周一闭馆，原定路线唯一可插入时段冲突</span>
                    </div>
                    <div className={styles.row}>
                      <span>重点保护场馆</span>
                      <span className={styles.highlightRed}>休馆维护中</span>
                    </div>
                  </>
                )}
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>{violation?.repair_hint || "调整游玩顺序将景点移至开放日，或暂时移除其中一个必去地点。"}</p>
              </div>
            </div>
          )}

          {isWalking && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>
                {violation?.message || "系统测算了市内景点间游览与换乘必需的最低步行距离，单日最低不可避免步行量超出了您的设定上限："}
              </p>
              <div className={styles.breakdownTable}>
                {breakdownList.length > 0 ? (
                  breakdownList.map((item, idx) => (
                    <div key={idx} className={styles.row}>
                      <span>{item.segment || "步行路段"}</span>
                      <strong>{item.meters ? `${(item.meters / 1000).toFixed(1)} km` : "1.0 km"}</strong>
                    </div>
                  ))
                ) : (
                  <>
                    <div className={styles.row}>
                      <span>街区漫步</span>
                      <strong>4.2 km</strong>
                    </div>
                    <div className={styles.row}>
                      <span>景区游览</span>
                      <strong>3.8 km</strong>
                    </div>
                    <div className={styles.row}>
                      <span>换乘站内必要步行</span>
                      <strong>1.3 km</strong>
                    </div>
                  </>
                )}
                <div className={`${styles.row} ${styles.totalRow}`}>
                  <span>单日最低不可避免步行量</span>
                  <span className={styles.highlightRed}>
                    {actualData.route_min_walking_meters ? `${((actualData.route_min_walking_meters as number) / 1000).toFixed(1)} km` : "9.3 km"}
                  </span>
                </div>
                <div className={`${styles.row} ${styles.limitRow}`}>
                  <span>您设置的每日步行上限</span>
                  <span className={styles.limitValue}>
                    {actualData.max_walking_meters ? `${((actualData.max_walking_meters as number) / 1000).toFixed(1)} km` : "5.0 km"}
                  </span>
                </div>
              </div>
              <div className={styles.suggestionBox}>
                <strong>建议调整方案</strong>
                <p>{violation?.repair_hint || "允许其中 1 天步行上限提升至 10 km，或增加出租车点对点接驳预算。"}</p>
              </div>
            </div>
          )}

          {!isBudget && !isHours && !isWalking && (
            <div className={styles.detailBody}>
              <p className={styles.desc}>{violation?.message || "检测到约束条件冲突。"}</p>
              {violation?.repair_hint && (
                <div className={styles.suggestionBox}>
                  <strong>建议调整方案</strong>
                  <p>{violation.repair_hint}</p>
                </div>
              )}
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
              onApplyFix(type);
              onClose();
            }}
          >
            应用此调整建议
          </button>
        </footer>
      </div>
    </div>
  );
}
