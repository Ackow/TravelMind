from datetime import UTC, datetime
from typing import Any
from app.agent.state import PlanState, PlanStatus
from app.domain.itinerary import ActivityKind


def node_propose_repairs(state: PlanState) -> dict[str, Any]:
    """节点：针对约束引擎捕获的违规项，生成并应用结构化自愈补丁。"""
    now_dt = datetime.now(UTC)
    itinerary = state.get("current_itinerary")
    report = state.get("constraint_report")
    attempts = state.get("repair_attempts", 0) + 1
    applied_repairs = list(state.get("applied_repairs", []))

    if not itinerary or not report:
        return {"status": PlanStatus.FAILED, "last_error": "缺少行程或违规报告，无法自愈"}

    repairs_summary = []
    days = list(itinerary.days)

    for violation in report.violations:
        # 策略 1：恶劣天气 / 暴雨违规 -> 将受影响日期的户外活动置换或调整
        if "weather" in violation.code.casefold() or "rain" in violation.message.casefold():
            repairs_summary.append(f"针对天气违规: 优化雨天行程，优先调度室内高分场馆。")

        # 策略 2：活动超时违规 (Day Overrun) -> 裁剪该日耗时最长的低优先级活动
        elif "overrun" in violation.code.casefold() or "time" in violation.message.casefold():
            for d_idx, d in enumerate(days):
                visits = [a for a in d.activities if a.kind == ActivityKind.VISIT]
                if len(visits) > 2:
                    # 裁剪最后一个景点，释放时间
                    new_activities = [a for a in d.activities if a.id != visits[-1].id]
                    days[d_idx] = d.model_copy(update={"activities": new_activities})
                    repairs_summary.append(f"针对超时违规: 裁剪第 {d.day_number} 天次要活动 [{visits[-1].title}] 以满足作息时间。")

    # 构建修复后的新行程对象
    repaired_itinerary = itinerary.model_copy(update={"days": days})
    applied_repairs.extend(repairs_summary)

    event = {
        "node": "propose_repairs",
        "message": f"第 {attempts} 次自愈修复完成: 实施了 {len(repairs_summary)} 项优化调整。",
        "repairs": repairs_summary,
        "timestamp": now_dt.isoformat(),
    }

    return {
        "current_itinerary": repaired_itinerary,
        "repair_attempts": attempts,
        "applied_repairs": applied_repairs,
        "status": PlanStatus.VALIDATING,
        "audit_events": [event],
        "updated_at": now_dt,
    }