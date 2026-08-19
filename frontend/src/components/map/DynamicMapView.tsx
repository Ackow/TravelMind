"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import { createPortal } from "react-dom";
import styles from "./map.module.css";

export interface TransitInfo {
  mode: string;
  duration: string;
  lineName?: string;
  entrance?: string;
}

export interface MapPoint {
  id: string;
  title: string;
  lat: number;
  lng: number;
  sequence: number;
  kind?: string;
  transitToNext?: TransitInfo;
}

export interface DayPointsGroup {
  dayNumber: number;
  theme?: string;
  points: MapPoint[];
}

export interface DynamicMapViewProps {
  destination: string;
  points: MapPoint[];
  currentDay?: number;
  allDaysPoints?: DayPointsGroup[];
  onSelectDay?: (dayIndex: number) => void;
  onSelectPoint?: (pointId: string) => void;
}

// 动态客户端加载 LeafletMap，避免 SSR 阶段 window / document 未定义报错
const LeafletMap = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className={styles.mapLoadingFallback}>
      <div className={styles.mapLoadingSpinner} />
      <span>正在加载真实地理图层...</span>
    </div>
  ),
});

export function DynamicMapView({
  destination,
  points,
  currentDay = 1,
  allDaysPoints,
  onSelectDay,
  onSelectPoint,
}: DynamicMapViewProps) {
  const [mounted, setMounted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [focusedPointId, setFocusedPointId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 监听 ESC 键退出全屏
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen]);

  const isDomestic = [
    "北京",
    "上海",
    "南京",
    "广州",
    "深圳",
    "杭州",
    "成都",
    "苏州",
    "武汉",
    "西安",
    "重庆",
  ].some((c) => destination.includes(c));

  const handleStopClick = (pId: string) => {
    setFocusedPointId(pId);
    onSelectPoint?.(pId);
  };

  return (
    <>
      {/* 1. 常规卡片地图视图 */}
      <div className={styles.mapWrapper} aria-label={`${destination} 真实交互路线图`}>
        <div className={styles.mapContainer}>
          {/* 当日标识 */}
          <div className={styles.dayBadge}>
            Day {currentDay} 路线 · {points.length} 个途经点
          </div>

          {/* 全屏展开查看按钮 */}
          <button
            type="button"
            className={styles.fullscreenBtn}
            onClick={() => setIsFullscreen(true)}
            title="点击全屏展开查看路线"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
            </svg>
            全屏查看
          </button>

          {mounted ? (
            <LeafletMap
              destination={destination}
              points={points}
              currentDay={currentDay}
              focusedPointId={focusedPointId}
              onSelectPoint={handleStopClick}
            />
          ) : (
            <div className={styles.mapLoadingFallback}>
              <div className={styles.mapLoadingSpinner} />
              <span>准备地图视图...</span>
            </div>
          )}

          {/* 底部数据源标识与交互提示 */}
          <div className={styles.mapBadge}>
            <Image
              src="/icons/attraction.svg"
              alt=""
              width={13}
              height={13}
              className={styles.mutedIcon}
            />
            <span>
              {isDomestic
                ? "高德地图高清底图"
                : "OpenStreetMap 免费全球矢量底图"}
            </span>
          </div>
        </div>
      </div>

      {/* 2. 全屏展开模态窗口 */}
      {isFullscreen && mounted && typeof document !== "undefined" && createPortal(
        <div className={styles.fullscreenOverlay} role="dialog" aria-modal="true">
          <header className={styles.fullscreenHeader}>
            <div className={styles.headerTitleGroup}>
              <strong>
                {destination} · Day {currentDay} 完整行程路线地图
              </strong>
              {/* 日程天数切换器 */}
              {allDaysPoints && allDaysPoints.length > 1 && (
                <div className={styles.dayTabs} aria-label="全屏日程切换">
                  {allDaysPoints.map((d, idx) => (
                    <button
                      key={d.dayNumber}
                      type="button"
                      className={`${styles.dayTab} ${
                        d.dayNumber === currentDay ? styles.dayTabActive : ""
                      }`}
                      onClick={() => {
                        onSelectDay?.(idx);
                        setFocusedPointId(null);
                      }}
                    >
                      Day {d.dayNumber}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              className={styles.closeBtn}
              onClick={() => setIsFullscreen(false)}
            >
              ✕ 退出全屏 (ESC)
            </button>
          </header>

          <div className={styles.fullscreenContent}>
            {/* 左侧浮动途经点与换乘列表 */}
            {points.length > 0 && (
              <div className={styles.floatingStopsList}>
                <div className={styles.floatingStopsTitle}>
                  <span>Day {currentDay} 途经站点 & 交通</span>
                  <small style={{ color: "#64748b", fontWeight: 600 }}>
                    共 {points.length} 站
                  </small>
                </div>
                {points.map((p, idx) => {
                  const isLast = idx === points.length - 1;
                  return (
                    <React.Fragment key={p.id}>
                      <div
                        className={`${styles.stopCard} ${
                          focusedPointId === p.id ? styles.stopCardActive : ""
                        }`}
                        onClick={() => handleStopClick(p.id)}
                        title="点击地图平滑居中查看"
                      >
                        <span className={styles.stopSeq}>
                          {p.sequence}
                        </span>
                        <div className={styles.stopInfo}>
                          <div className={styles.stopTitle}>{p.title}</div>
                          <div className={styles.stopKind}>{p.kind || "景点游览"}</div>
                        </div>
                      </div>

                      {/* 站点之间的换乘交通指示 */}
                      {!isLast && p.transitToNext && (
                        <div className={styles.transitStepConnector}>
                          <div className={styles.transitLineDashed} />
                          <div className={styles.transitStepBadge}>
                            <Image
                              src={p.transitToNext.mode.includes("步行") ? "/icons/walking.svg" : "/icons/train.svg"}
                              alt=""
                              width={13}
                              height={13}
                              className={styles.mutedIcon}
                            />
                            <span>{p.transitToNext.mode}</span>
                            {p.transitToNext.lineName && (
                              <span className={styles.transitSubText}>
                                ({p.transitToNext.lineName})
                              </span>
                            )}
                            <span className={styles.transitDuration}>
                              · {p.transitToNext.duration}
                            </span>
                          </div>
                        </div>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            )}

            {/* 全屏地图画布 */}
            {mounted && (
              <LeafletMap
                destination={destination}
                points={points}
                currentDay={currentDay}
                focusedPointId={focusedPointId}
                onSelectPoint={handleStopClick}
              />
            )}
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
