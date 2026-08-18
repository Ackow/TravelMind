"use client";

import styles from "./mini-route-map.module.css";

export function MiniRouteMap() {
  return (
    <div className={styles.mapContainer} aria-label="东京行程路线简图">
      <svg
        viewBox="0 0 320 180"
        className={styles.mapSvg}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Soft Land Mass / City Grid Backdrop */}
        <rect width="320" height="180" rx="10" fill="#f4f8f6" />

        {/* Soft Road Grid Lines */}
        <g stroke="#e2ece7" strokeWidth="1.2" opacity="0.8">
          <line x1="20" y1="0" x2="20" y2="180" />
          <line x1="70" y1="0" x2="70" y2="180" />
          <line x1="120" y1="0" x2="120" y2="180" />
          <line x1="180" y1="0" x2="180" y2="180" />
          <line x1="240" y1="0" x2="240" y2="180" />
          <line x1="290" y1="0" x2="290" y2="180" />

          <line x1="0" y1="35" x2="320" y2="35" />
          <line x1="0" y1="75" x2="320" y2="75" />
          <line x1="0" y1="115" x2="320" y2="115" />
          <line x1="0" y1="155" x2="320" y2="155" />
        </g>

        {/* Tokyo Bay Water Polygon on the Right/Bottom */}
        <path
          d="M260 0 C 275 60, 265 110, 320 150 L 320 0 Z"
          fill="#dcebe5"
          opacity="0.9"
        />
        <path
          d="M280 140 C 250 160, 260 180, 290 180 L 320 180 L 320 140 Z"
          fill="#dcebe5"
          opacity="0.9"
        />

        {/* Route Connection Paths in Deep Teal */}
        {/* Upper Route: 1 (上野) -> 3 (浅草) -> 2 (秋叶原) -> 5 (银座) -> 4 (涩谷) */}
        <path
          d="M100 50 L 175 30 L 210 60 L 195 135 L 75 125"
          stroke="#123f3a"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Outer Glowing / Translucent Subway Trace */}
        <path
          d="M100 50 L 175 30 L 210 60 L 195 135 L 75 125"
          stroke="#059669"
          strokeWidth="6.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.22"
        />

        {/* Numbered Stops */}

        {/* 1. 上野 (Ueno) */}
        <g transform="translate(100, 50)">
          <circle cx="0" cy="0" r="9" fill="#123f3a" />
          <text x="0" y="3.5" fill="#ffffff" fontSize="9" fontWeight="800" textAnchor="middle">
            1
          </text>
          <rect x="-18" y="11" width="36" height="15" rx="4" fill="#ffffff" opacity="0.9" />
          <text x="0" y="22" fill="#102e2a" fontSize="9.5" fontWeight="750" textAnchor="middle">
            上野
          </text>
        </g>

        {/* 3. 浅草 (Asakusa) */}
        <g transform="translate(175, 30)">
          <circle cx="0" cy="0" r="9" fill="#123f3a" />
          <text x="0" y="3.5" fill="#ffffff" fontSize="9" fontWeight="800" textAnchor="middle">
            3
          </text>
          <rect x="11" y="-6" width="34" height="15" rx="4" fill="#ffffff" opacity="0.9" />
          <text x="28" y="5" fill="#102e2a" fontSize="9.5" fontWeight="750" textAnchor="middle">
            浅草
          </text>
        </g>

        {/* 2. 秋叶原 (Akihabara) */}
        <g transform="translate(210, 60)">
          <circle cx="0" cy="0" r="9" fill="#123f3a" />
          <text x="0" y="3.5" fill="#ffffff" fontSize="9" fontWeight="800" textAnchor="middle">
            2
          </text>
          <rect x="-38" y="-18" width="42" height="15" rx="4" fill="#ffffff" opacity="0.9" />
          <text x="-17" y="-7" fill="#102e2a" fontSize="9.5" fontWeight="750" textAnchor="middle">
            秋叶原
          </text>
        </g>

        {/* 5. 银座 (Ginza) */}
        <g transform="translate(195, 135)">
          <circle cx="0" cy="0" r="9" fill="#123f3a" />
          <text x="0" y="3.5" fill="#ffffff" fontSize="9" fontWeight="800" textAnchor="middle">
            5
          </text>
          <rect x="-18" y="11" width="36" height="15" rx="4" fill="#ffffff" opacity="0.9" />
          <text x="0" y="22" fill="#102e2a" fontSize="9.5" fontWeight="750" textAnchor="middle">
            银座
          </text>
        </g>

        {/* 4. 涩谷 (Shibuya) */}
        <g transform="translate(75, 125)">
          <circle cx="0" cy="0" r="9" fill="#123f3a" />
          <text x="0" y="3.5" fill="#ffffff" fontSize="9" fontWeight="800" textAnchor="middle">
            4
          </text>
          <rect x="-18" y="11" width="36" height="15" rx="4" fill="#ffffff" opacity="0.9" />
          <text x="0" y="22" fill="#102e2a" fontSize="9.5" fontWeight="750" textAnchor="middle">
            涩谷
          </text>
        </g>
      </svg>
    </div>
  );
}
