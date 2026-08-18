from typing import Literal
from app.agent.state import PlanState, PlanStatus


def route_after_constraints(state: PlanState) -> Literal["prepare_review", "propose_repairs", "failed"]:
    """条件边：根据约束引擎审计结果与修复尝试次数决定流向。"""
    if state.get("status") == PlanStatus.FAILED:
        return "failed"

    report = state.get("constraint_report")
    attempts = state.get("repair_attempts", 0)
    max_attempts = state.get("max_repair_attempts", 3)

    # 约束全部满足 -> 直接进入审阅
    if report and report.passed:
        return "prepare_review"

    # 存在违规但未达到修复上限 -> 进入自愈修复循环
    if attempts < max_attempts:
        return "propose_repairs"

    # 达到最大修复尝试仍未完全解决 -> 降级呈现给用户审阅（说明妥协原因）
    return "prepare_review"


def route_after_human_interrupt(state: PlanState) -> Literal["end", "handle_feedback"]:
    """条件边：根据用户审阅动作（批准 vs 修改意见）分流。"""
    if state.get("status") == PlanStatus.APPROVED:
        return "end"
    return "handle_feedback"