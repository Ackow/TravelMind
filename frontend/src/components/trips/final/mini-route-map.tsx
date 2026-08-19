"use client";

import React, { useMemo } from "react";
import { DynamicMapView, type MapPoint, type DayPointsGroup } from "@/components/map/DynamicMapView";
import styles from "./mini-route-map.module.css";

interface MiniRouteMapProps {
  destination?: string;
  points?: MapPoint[];
  currentDay?: number;
  allDaysPoints?: DayPointsGroup[];
  onSelectDay?: (dayIndex: number) => void;
  onSelectPoint?: (pointId: string) => void;
}

export function MiniRouteMap({
  destination = "南京",
  points,
  currentDay = 1,
  allDaysPoints,
  onSelectDay,
  onSelectPoint,
}: MiniRouteMapProps) {
  // 根据当前选中天数动态获取该天的所有活动地图点位
  const activePoints = useMemo(() => {
    if (points && points.length > 0) return points;
    if (allDaysPoints && allDaysPoints.length > 0) {
      const match = allDaysPoints.find((g) => g.dayNumber === currentDay);
      return match ? match.points : allDaysPoints[0].points;
    }
    return [];
  }, [points, allDaysPoints, currentDay]);

  return (
    <div className={styles.mapContainer} aria-label={`${destination} Day ${currentDay} 行程路线地图`}>
      {/* 顶部天数切换按钮条 */}
      {allDaysPoints && allDaysPoints.length > 1 && (
        <div className={styles.dayTabsBar} aria-label="日程天数切换">
          {allDaysPoints.map((d, idx) => (
            <button
              key={d.dayNumber}
              type="button"
              className={`${styles.dayTabBtn} ${d.dayNumber === currentDay ? styles.dayTabBtnActive : ""}`}
              onClick={() => onSelectDay?.(idx)}
            >
              Day {d.dayNumber}
            </button>
          ))}
        </div>
      )}
      <DynamicMapView
        destination={destination}
        points={activePoints}
        currentDay={currentDay}
        allDaysPoints={allDaysPoints}
        onSelectDay={onSelectDay}
        onSelectPoint={onSelectPoint}
      />
    </div>
  );
}
