"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { PageBreadcrumb } from "@/components/system/page-breadcrumb";
import {
  getTrip,
  getCurrentPlan,
  createFeedback,
  type TripResponse,
  type PlanVersionResponse,
} from "@/lib/api/trips";
import {
  ConflictDetailModal,
  type ConflictType,
} from "./conflict-detail-modal";
import styles from "./conflict-resolution.module.css";

interface ConflictResolutionProps {
  tripId?: string;
}

export function ConflictResolution({
  tripId = "88888888-8888-8888-8888-888888888888",
}: ConflictResolutionProps) {
  const router = useRouter();

  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [plan, setPlan] = useState<PlanVersionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // State management for interactions
  const [selectedOption, setSelectedOption] = useState<string>("budget");
  const [customFeedback, setCustomFeedback] = useState<string>("");
  const [activeModal, setActiveModal] = useState<ConflictType | null>(null);
  const [copyToast, setCopyToast] = useState(false);
  const [isReoptimizing, setIsReoptimizing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const targetId = tripId || "88888888-8888-8888-8888-888888888888";
    setLoading(true);

    Promise.all([
      getTrip(targetId).catch(() => null),
      getCurrentPlan(targetId).catch(() => null),
    ]).then(([tripRes, planRes]) => {
      if (!active) return;
      if (tripRes) setTrip(tripRes);
      if (planRes) setPlan(planRes);
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [tripId]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2800);
  };

  const requestId = trip?.active_planning_run_id || (plan ? `REQ-${plan.id.slice(0, 8)}` : "REQ-8F3A2B7C");
  const generateTime = plan?.created_at ? plan.created_at.slice(0, 16).replace("T", " ") : "2026-10-01 14:32";

  const handleCopyRequestId = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(requestId);
    }
    setCopyToast(true);
    showToast("请求 ID 已复制到剪贴板");
    setTimeout(() => setCopyToast(false), 2000);
  };

  const handleReplan = async () => {
    setIsReoptimizing(true);
    showToast("正在根据新约束条件重新规划行程...");

    const targetId = trip?.id || tripId;
    const baseVersion = plan?.version || 1;

    try {
      let operations: Array<Record<string, unknown>> = [];

      if (selectedOption === "budget") {
        operations = [
          {
            op: "set_budget",
            amount: 1120000,
            currency: "CNY",
            reason: "用户同意将预算提高至 ¥11,200 以保留所有必选地点",
          },
        ];
      } else if (selectedOption === "walking") {
        operations = [
          {
            op: "set_max_walking",
            meters_per_day: 10000,
            reason: "用户允许其中一天步行上限放宽至 10 km",
          },
        ];
      } else if (selectedOption === "remove_poi") {
        operations = [
          {
            op: "remove_required_place",
            place_name: "重点保护场馆",
            reason: "用户同意暂时移除休馆场馆",
          },
        ];
      }

      if (customFeedback.trim()) {
        operations.push({
          op: "custom_note",
          note: customFeedback.trim(),
        });
      }

      await createFeedback(targetId, {
        base_plan_version: baseVersion,
        message: `用户在冲突诊断中选择了调整方案：${selectedOption}。${customFeedback.trim()}`,
        client_operations: operations,
        auto_start_replanning: true,
      });

      showToast("重新规划任务已提交！正在跳转至行程视图...");
      setTimeout(() => {
        router.push(`/trips/${targetId}`);
      }, 1000);
    } catch {
      showToast("重新规划中... 正在为您生成更新后的行程草案");
      setTimeout(() => {
        setIsReoptimizing(false);
        router.push(`/trips/${targetId}`);
      }, 1200);
    }
  };

  const handleApplyFixFromModal = (fixType: string) => {
    setSelectedOption(fixType === "places" ? "remove_poi" : fixType);
    showToast(`已选定调整方案：${
      fixType === "budget"
        ? "将预算提高至 ¥11,200"
        : fixType === "walking"
        ? "允许其中一天步行最多 10 km"
        : "移除一个必去地点"
    }`);
  };

  const breadcrumbItems = [
    { label: "我的旅行", href: "/" },
    { label: "旅行规划详情", href: `/trips/${trip?.id || tripId}` },
    { label: "规划结果" },
  ];

  const retainedInterests = trip?.preferences?.interests?.length
    ? trip.preferences.interests
    : [
        { value: "动漫", weight: 0.9 },
        { value: "美食", weight: 0.8 },
        { value: "少购物", weight: 0.7 },
      ];

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.contentWrapper} style={{ padding: "60px 0", textAlign: "center" }}>
          <p style={{ fontSize: "16px", color: "var(--color-text-secondary, #666)" }}>
            正在加载硬约束冲突诊断数据...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      {/* Toast Alert */}
      {toastMessage && (
        <div className={styles.toast} role="alert">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{toastMessage}</span>
        </div>
      )}

      <div className={styles.contentWrapper}>
        {/* Breadcrumb Navigation */}
        <PageBreadcrumb items={breadcrumbItems} />

        {/* Hero Section */}
        <header className={styles.heroSection}>
          <div className={styles.heroLeft}>
            <h1 className={styles.heroTitle}>当前条件下无法生成可行计划</h1>
            <div className={styles.heroDesc}>
              <p>我们没有忽略你的要求。</p>
              <p>以下硬性约束彼此冲突，请选择要调整的项目。</p>
            </div>
          </div>

          <div className={styles.heroRight}>
            <Image
              src="/icons/warning-illustration.svg"
              alt=""
              width={200}
              height={140}
              priority
              className={styles.warningIllustration}
            />
          </div>
        </header>

        {/* Two-Column Responsive Layout */}
        <div className={styles.mainGrid}>
          {/* Left Column: Conflicts List & Adjustment Options */}
          <div className={styles.leftCol}>
            {/* Card 1: 发现 3 个冲突 */}
            <section className={styles.card} aria-labelledby="conflict-title">
              <h2 id="conflict-title" className={styles.cardTitle}>
                发现 3 个冲突
              </h2>

              <div className={styles.conflictListWrapper}>
                {/* Conflict 1: 总预算不足 */}
                <div className={styles.conflictRow}>
                  <div className={styles.conflictTop}>
                    <div className={styles.conflictTitleArea}>
                      <div className={styles.conflictIconBadge}>
                        <Image
                          src="/icons/wallet.svg"
                          alt=""
                          width={22}
                          height={22}
                          className={styles.coralIconFilter}
                          aria-hidden="true"
                        />
                      </div>
                      <strong className={styles.conflictName}>总预算不足</strong>
                    </div>

                    <div className={styles.comparisonArea}>
                      <div className={styles.compItemLeft}>
                        <span className={styles.primaryVal}>预计最低 ¥11,200</span>
                      </div>

                      <div className={styles.vsPill}>VS</div>

                      <div className={styles.compItemRight}>
                        <span className={styles.primaryVal}>
                          ¥{trip ? (trip.constraints.total_budget.amount / 100).toLocaleString() : "10,000"}
                        </span>
                        <span className={styles.subLabel}>你的上限</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      className={styles.viewDetailBtn}
                      onClick={() => setActiveModal("budget")}
                    >
                      <span>查看详情</span>
                      <Image
                        src="/icons/chevron-right.svg"
                        alt=""
                        width={14}
                        height={14}
                        className={styles.tealIconFilter}
                        aria-hidden="true"
                      />
                    </button>
                  </div>

                  <p className={styles.conflictExplain}>
                    当前行程需求与必去选择超过了可用预算。
                  </p>
                </div>

                {/* Conflict 2: 必去地点营业时间冲突 */}
                <div className={styles.conflictRow}>
                  <div className={styles.conflictTop}>
                    <div className={styles.conflictTitleArea}>
                      <div className={styles.conflictIconBadge}>
                        <Image
                          src="/icons/clock.svg"
                          alt=""
                          width={22}
                          height={22}
                          className={styles.coralIconFilter}
                          aria-hidden="true"
                        />
                      </div>
                      <strong className={styles.conflictName}>必去地点营业时间冲突</strong>
                    </div>

                    <div className={styles.comparisonArea}>
                      <div className={styles.compItemLeft}>
                        <span className={styles.subLabel}>仅有可用日</span>
                        <span className={styles.primaryVal}>第 3 天 (周三)</span>
                      </div>

                      <div className={styles.vsPill}>VS</div>

                      <div className={styles.compItemRight}>
                        <span className={styles.primaryVal}>2 个必去地点</span>
                        <span className={styles.subLabel}>该日闭馆</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      className={styles.viewDetailBtn}
                      onClick={() => setActiveModal("hours")}
                    >
                      <span>查看详情</span>
                      <Image
                        src="/icons/chevron-right.svg"
                        alt=""
                        width={14}
                        height={14}
                        className={styles.tealIconFilter}
                        aria-hidden="true"
                      />
                    </button>
                  </div>

                  <p className={styles.conflictExplain}>
                    唯一可安排的时间窗口与必去地点的营业时间冲突。
                  </p>
                </div>

                {/* Conflict 3: 每日步行上限过低 */}
                <div className={styles.conflictRow}>
                  <div className={styles.conflictTop}>
                    <div className={styles.conflictTitleArea}>
                      <div className={styles.conflictIconBadge}>
                        <Image
                          src="/icons/walking.svg"
                          alt=""
                          width={22}
                          height={22}
                          className={styles.coralIconFilter}
                          aria-hidden="true"
                        />
                      </div>
                      <strong className={styles.conflictName}>每日步行上限过低</strong>
                    </div>

                    <div className={styles.comparisonArea}>
                      <div className={styles.compItemLeft}>
                        <span className={styles.subLabel}>路线最低</span>
                        <span className={styles.primaryVal}>9.3 km</span>
                      </div>

                      <div className={styles.vsPill}>VS</div>

                      <div className={styles.compItemRight}>
                        <span className={styles.primaryVal}>
                          {trip?.constraints.max_walking_meters_per_day ? `${(trip.constraints.max_walking_meters_per_day / 1000).toFixed(0)} km` : "5 km"}
                        </span>
                        <span className={styles.subLabel}>你的上限</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      className={styles.viewDetailBtn}
                      onClick={() => setActiveModal("walking")}
                    >
                      <span>查看详情</span>
                      <Image
                        src="/icons/chevron-right.svg"
                        alt=""
                        width={14}
                        height={14}
                        className={styles.tealIconFilter}
                        aria-hidden="true"
                      />
                    </button>
                  </div>

                  <p className={styles.conflictExplain}>
                    在当前步行约束下，无法完成行程路线。
                  </p>
                </div>
              </div>
            </section>

            {/* Card 2: 你可以这样调整 */}
            <section className={styles.card} aria-labelledby="adjust-title">
              <h2 id="adjust-title" className={styles.cardTitle}>
                你可以这样调整
              </h2>

              <div className={styles.adjustOptionsGrid}>
                {/* Option 1: 提高预算 */}
                <div
                  className={`${styles.adjustCard} ${
                    selectedOption === "budget" ? styles.adjustCardActive : ""
                  }`}
                  onClick={() => setSelectedOption("budget")}
                  role="radio"
                  aria-checked={selectedOption === "budget"}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") setSelectedOption("budget");
                  }}
                >
                  <div className={styles.radioIndicator}>
                    <div className={`${styles.radioCircle} ${selectedOption === "budget" ? styles.radioCircleActive : ""}`}>
                      {selectedOption === "budget" && <div className={styles.radioDot} />}
                    </div>
                  </div>

                  <div className={styles.adjustIconArea}>
                    <Image
                      src="/icons/wallet.svg"
                      alt=""
                      width={20}
                      height={20}
                      className={styles.emeraldIconFilter}
                      aria-hidden="true"
                    />
                  </div>

                  <span className={styles.adjustText}>将预算提高至 ¥11,200</span>

                  <span className={styles.recomTag}>推荐</span>
                </div>

                {/* Option 2: 允许步行最多 10 km */}
                <div
                  className={`${styles.adjustCard} ${
                    selectedOption === "walking" ? styles.adjustCardActive : ""
                  }`}
                  onClick={() => setSelectedOption("walking")}
                  role="radio"
                  aria-checked={selectedOption === "walking"}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") setSelectedOption("walking");
                  }}
                >
                  <div className={styles.radioIndicator}>
                    <div className={`${styles.radioCircle} ${selectedOption === "walking" ? styles.radioCircleActive : ""}`}>
                      {selectedOption === "walking" && <div className={styles.radioDot} />}
                    </div>
                  </div>

                  <div className={styles.adjustIconArea}>
                    <Image
                      src="/icons/walking.svg"
                      alt=""
                      width={20}
                      height={20}
                      className={styles.emeraldIconFilter}
                      aria-hidden="true"
                    />
                  </div>

                  <span className={styles.adjustText}>允许其中一天步行最多 10 km</span>
                </div>

                {/* Option 3: 移除一个必去地点 */}
                <div
                  className={`${styles.adjustCard} ${
                    selectedOption === "remove_poi" ? styles.adjustCardActive : ""
                  }`}
                  onClick={() => setSelectedOption("remove_poi")}
                  role="radio"
                  aria-checked={selectedOption === "remove_poi"}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") setSelectedOption("remove_poi");
                  }}
                >
                  <div className={styles.radioIndicator}>
                    <div className={`${styles.radioCircle} ${selectedOption === "remove_poi" ? styles.radioCircleActive : ""}`}>
                      {selectedOption === "remove_poi" && <div className={styles.radioDot} />}
                    </div>
                  </div>

                  <div className={styles.adjustIconArea}>
                    <Image
                      src="/icons/map-pin.svg"
                      alt=""
                      width={20}
                      height={20}
                      className={styles.emeraldIconFilter}
                      aria-hidden="true"
                    />
                  </div>

                  <span className={styles.adjustText}>移除一个必去地点</span>
                </div>
              </div>

              {/* Free Text Input */}
              <div className={styles.customInputBox}>
                <div className={styles.inputIconArea}>
                  <Image
                    src="/icons/feedback-chat.svg"
                    alt=""
                    width={18}
                    height={18}
                    className={styles.mutedIconFilter}
                    aria-hidden="true"
                  />
                </div>
                <input
                  type="text"
                  className={styles.feedbackField}
                  placeholder="或者告诉我你愿意怎样调整..."
                  value={customFeedback}
                  maxLength={200}
                  onChange={(e) => setCustomFeedback(e.target.value)}
                />
                <span className={styles.charCount}>{customFeedback.length}/200</span>
              </div>

              {/* Action Buttons */}
              <div className={styles.btnRow}>
                <button
                  type="button"
                  className={styles.backButton}
                  onClick={() => router.push(`/trips/new`)}
                >
                  返回修改条件
                </button>

                <button
                  type="button"
                  className={`${styles.replanButton} ${isReoptimizing ? styles.replanLoading : ""}`}
                  onClick={handleReplan}
                  disabled={isReoptimizing}
                >
                  {isReoptimizing ? (
                    <span className={styles.spinnerWrapper}>
                      <span className={styles.loadingSpin} />
                      重新规划中...
                    </span>
                  ) : (
                    "按所选条件重新规划"
                  )}
                </button>
              </div>
            </section>
          </div>

          {/* Right Column: Matched height */}
          <aside className={styles.rightCol} aria-labelledby="retained-title">
            <div className={`${styles.card} ${styles.rightCard}`}>
              <div className={styles.rightCardTop}>
                <h2 id="retained-title" className={styles.cardTitle}>
                  我们仍然保留
                </h2>

                <p className={styles.retainedDesc}>
                  你的偏好与喜好将继续保留。
                </p>

                {/* Preference Items with unified teal colors */}
                <div className={styles.retainedList}>
                  {retainedInterests.map((item) => (
                    <div key={item.value} className={styles.retainedItem}>
                      <div className={styles.prefCircleBadge}>
                        <Image
                          src={
                            item.value.includes("漫")
                              ? "/icons/anime.svg"
                              : item.value.includes("食") || item.value.includes("餐")
                              ? "/icons/meal.svg"
                              : item.value.includes("购")
                              ? "/icons/shopping.svg"
                              : "/icons/attraction.svg"
                          }
                          alt=""
                          width={22}
                          height={22}
                          className={styles.tealIconFilter}
                          aria-hidden="true"
                        />
                      </div>
                      <strong className={styles.retainedLabel}>{item.value}</strong>
                    </div>
                  ))}
                </div>

                {/* Info Callout */}
                <div className={styles.infoBanner}>
                  <div className={styles.infoIconArea}>
                    <Image
                      src="/icons/info-circle.svg"
                      alt=""
                      width={18}
                      height={18}
                      className={styles.infoIconFilter}
                      aria-hidden="true"
                    />
                  </div>
                  <p className={styles.infoText}>
                    除非你确认调整，我们不会移除任何你的要求。
                  </p>
                </div>
              </div>

              {/* Support Info pinned to bottom of right card */}
              <div className={styles.supportMeta}>
                <h3 className={styles.supportTitle}>支持信息</h3>
                <div className={styles.metaRow}>
                  <span>请求 ID: <span className={styles.metaValue}>{requestId}</span></span>
                  <button
                    type="button"
                    className={styles.copyIconButton}
                    onClick={handleCopyRequestId}
                    title="复制请求 ID"
                    aria-label="复制请求 ID"
                  >
                    {copyToast ? (
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <Image
                        src="/icons/copy-id.svg"
                        alt=""
                        width={15}
                        height={15}
                        className={styles.mutedIconFilter}
                        aria-hidden="true"
                      />
                    )}
                  </button>
                </div>
                <div className={styles.metaRow}>
                  <span>生成时间: <span className={styles.metaValue}>{generateTime}</span></span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* Conflict Diagnostic Detail Modal */}
      <ConflictDetailModal
        type={activeModal}
        onClose={() => setActiveModal(null)}
        onApplyFix={handleApplyFixFromModal}
      />
    </div>
  );
}
