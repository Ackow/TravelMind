"use client";

import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { type MapPoint } from "./DynamicMapView";

interface LeafletMapProps {
  destination: string;
  points: MapPoint[];
  currentDay?: number;
  focusedPointId?: string | null;
  onSelectPoint?: (pointId: string) => void;
}

// 预设基准中心坐标
const DEFAULT_CENTERS: Record<string, [number, number]> = {
  南京: [32.0603, 118.7969],
  杭州: [30.2741, 120.1551],
  北京: [39.9042, 116.4074],
  上海: [31.2304, 121.4737],
  成都: [30.5728, 104.0668],
  广州: [23.1291, 113.2644],
  深圳: [22.5431, 114.0579],
  苏州: [31.2989, 120.5853],
  西安: [34.3416, 108.9398],
  重庆: [29.5630, 106.5516],
  武汉: [30.5928, 114.3055],
  Tokyo: [35.6895, 139.6917],
  东京: [35.6895, 139.6917],
};

export default function LeafletMap({
  destination,
  points,
  focusedPointId,
  onSelectPoint,
}: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const markersRef = useRef<Record<string, L.Marker>>({});

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

  // 1. 初始化地图实例
  useEffect(() => {
    if (!containerRef.current) return;
    if (mapInstanceRef.current) return;

    const fallbackCenter = DEFAULT_CENTERS[destination] || [32.0603, 118.7969];
    const initialCenter: [number, number] =
      points.length > 0 ? [points[0].lat, points[0].lng] : fallbackCenter;

    const map = L.map(containerRef.current, {
      center: initialCenter,
      zoom: 13,
      zoomControl: false,
    });

    // 缩放控件放在右下角，避免与右上角全屏按钮重叠
    L.control.zoom({ position: "bottomright" }).addTo(map);

    // 根据境内外选择免费高速瓦片源
    if (isDomestic) {
      // 高德地图免费底图瓦片 (国内极速加载，无 CORS 限制)
      L.tileLayer(
        "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
        {
          subdomains: ["1", "2", "3", "4"],
          maxZoom: 18,
          minZoom: 3,
          attribution: '&copy; <a href="https://www.amap.com">高德地图</a>',
        }
      ).addTo(map);
    } else {
      // CartoDB / OpenStreetMap 免费全球矢量渲染瓦片 (无需 API Key)
      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        {
          subdomains: "abcd",
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO',
        }
      ).addTo(map);
    }

    const layerGroup = L.layerGroup().addTo(map);
    layerGroupRef.current = layerGroup;
    mapInstanceRef.current = map;

    // 延时自适应容器尺寸
    setTimeout(() => {
      map.invalidateSize();
    }, 100);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
      markersRef.current = {};
    };
  }, [destination, isDomestic]);

  // 2. 当切日或点位数据更新时重新绘制 Marker 和 Polyline 轨迹
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    map.invalidateSize();
    layerGroup.clearLayers();
    markersRef.current = {};

    if (points.length === 0) {
      const center = DEFAULT_CENTERS[destination] || [32.0603, 118.7969];
      map.setView(center, 12, { animate: true });
      return;
    }

    const latLngs: [number, number][] = points.map((p) => [p.lat, p.lng]);

    // 绘制多方式分段轨迹连线 (按地铁、步行、高铁、公交/打车区分颜色与线型)
    if (points.length > 1) {
      for (let i = 0; i < points.length - 1; i++) {
        const p1 = points[i];
        const p2 = points[i + 1];
        const mode = p1.transitToNext?.mode || "";
        const segCoords: [number, number][] = [
          [p1.lat, p1.lng],
          [p2.lat, p2.lng],
        ];

        if (mode.includes("地铁")) {
          // 地铁：明亮天蓝色实线，配发光光晕
          L.polyline(segCoords, {
            color: "#38bdf8",
            weight: 7,
            opacity: 0.35,
            lineCap: "round",
            lineJoin: "round",
          }).addTo(layerGroup);
          L.polyline(segCoords, {
            color: "#0284c7",
            weight: 4.5,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
          }).addTo(layerGroup);
        } else if (mode.includes("步行")) {
          // 步行：翠绿色点虚线
          L.polyline(segCoords, {
            color: "#10b981",
            weight: 3.5,
            opacity: 0.9,
            dashArray: "4, 6",
            lineCap: "round",
            lineJoin: "round",
          }).addTo(layerGroup);
        } else if (mode.includes("高铁") || mode.includes("城际")) {
          // 高铁：深色加粗双线
          L.polyline(segCoords, {
            color: "#0f766e",
            weight: 5.5,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
          }).addTo(layerGroup);
        } else {
          // 公交 / 打车 / 观光车：琥珀色虚线
          L.polyline(segCoords, {
            color: "#f59e0b",
            weight: 4,
            opacity: 0.9,
            dashArray: "8, 4",
            lineCap: "round",
            lineJoin: "round",
          }).addTo(layerGroup);
        }

        // 如果有地铁口或者站点入口标注，绘制轻量入口小标记
        if (p1.transitToNext?.entrance) {
          const entranceLat = p1.lat + (p2.lat - p1.lat) * 0.15;
          const entranceLng = p1.lng + (p2.lng - p1.lng) * 0.15;

          const entranceIcon = L.divIcon({
            className: "metro-entrance-pin",
            html: `
              <div style="
                display: inline-flex;
                align-items: center;
                gap: 3px;
                background: #0284c7;
                color: #ffffff;
                font-size: 10.5px;
                font-weight: 750;
                padding: 2px 7px;
                border-radius: 5px;
                border: 1.5px solid #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                white-space: nowrap;
                pointer-events: none;
              ">
                <span>🚇</span>
                <span>${p1.transitToNext.entrance}</span>
              </div>
            `,
            iconSize: [84, 22],
            iconAnchor: [42, 11],
          });

          L.marker([entranceLat, entranceLng], { icon: entranceIcon }).addTo(layerGroup);
        }
      }
    }

    // 绘制带序号的自定义圆点 Pin Marker
    points.forEach((point) => {
      const isHotelOrStation = point.kind === "酒店" || point.kind === "高铁站" || point.kind === "交通枢纽";
      const pinBg = isHotelOrStation ? "#0f766e" : "#10b981";

      const customIcon = L.divIcon({
        className: "custom-map-pin",
        html: `
          <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: ${pinBg};
            color: #ffffff;
            font-size: 12px;
            font-weight: 800;
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            cursor: pointer;
            transition: transform 0.2s ease;
          ">
            ${point.sequence}
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -16],
      });

      const marker = L.marker([point.lat, point.lng], { icon: customIcon });
      marker.bindPopup(`
        <div style="font-family: inherit; font-size: 13px; min-width: 150px; padding: 2px;">
          <strong style="color: #0f172a; font-size: 14px;">${point.title}</strong>
          <div style="color: #64748b; font-size: 12px; margin-top: 4px;">
            第 ${point.sequence} 站 · ${point.kind || "景点游览"}
          </div>
        </div>
      `);

      marker.on("click", () => {
        onSelectPoint?.(point.id);
      });

      marker.addTo(layerGroup);
      markersRef.current[point.id] = marker;
    });

    // 自动平滑调整视野
    if (latLngs.length === 1) {
      map.setView(latLngs[0], 14, { animate: true });
    } else {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, {
        padding: [45, 45],
        maxZoom: 15,
        animate: true,
      });
    }
  }, [points, destination, onSelectPoint]);

  // 3. 当选定特定地点时平滑移动居中并弹出气泡
  useEffect(() => {
    if (!focusedPointId) return;
    const map = mapInstanceRef.current;
    const marker = markersRef.current[focusedPointId];
    const targetPoint = points.find((p) => p.id === focusedPointId);
    if (map && targetPoint) {
      map.flyTo([targetPoint.lat, targetPoint.lng], 16, {
        animate: true,
        duration: 0.8,
      });
      if (marker) {
        setTimeout(() => {
          marker.openPopup();
        }, 350);
      }
    }
  }, [focusedPointId, points]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%", minHeight: "260px" }} />;
}
