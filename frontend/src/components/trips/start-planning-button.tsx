"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { startPlanning, type PlanningRunResponse } from "@/lib/api/trips";

export function StartPlanningButton({ tripId }: { tripId: string }) {
  const router = useRouter();
  const [run, setRun] = useState<PlanningRunResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setPending(true);
    setError(null);
    try {
      const result = await startPlanning(tripId);
      setRun(result);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "规划失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <button type="button" onClick={handleClick} disabled={pending}>
        {pending ? "正在规划…" : "生成旅行计划"}
      </button>
      {error && <p role="alert">{error}</p>}
      {run && (
        <p aria-live="polite">
          运行状态：{run.status}；计划版本：
          {run.result_plan_version}
        </p>
      )}
    </div>
  );
}
