"use client";

import { useEffect, useState } from "react";

import { getTrip, type TripResponse } from "@/lib/api/trips";
import { StartPlanningButton } from "./start-planning-button";
import { CurrentPlan } from "./current-plan";

export function TripDetail({ tripId }: { tripId: string }) {
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getTrip(tripId)
      .then((result) => {
        if (active) {
          setTrip(result);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "读取失败");
        }
      });

    return () => {
      active = false;
    };
  }, [tripId]);

  if (error) {
    return <p role="alert">{error}</p>;
  }
  if (!trip) {
    return <p>正在读取旅行…</p>;
  }

  if (trip.current_plan_version !== null) {
    return <CurrentPlan trip={trip} />;
  }

  return (
    <section>
      <h1>{trip.destination}旅行</h1>
      <dl>
        <dt>旅行 ID</dt>
        <dd>{trip.id}</dd>
        <dt>出发地</dt>
        <dd>{trip.origin}</dd>
        <dt>人数</dt>
        <dd>{trip.travelers}</dd>
        <dt>状态</dt>
        <dd>{trip.status}</dd>
      </dl>
      {trip.status === "draft" && trip.current_plan_version === null ? (
        <StartPlanningButton tripId={trip.id} />
      ) : trip.status === "planning" ? (
        <p aria-live="polite">正在生成旅行计划…</p>
      ) : (
        <p aria-live="polite">
          旅行计划已生成，当前版本为 {trip.current_plan_version}，等待审阅。
        </p>
      )}
    </section>
  );
}
