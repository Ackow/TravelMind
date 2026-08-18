from datetime import UTC, datetime
from typing import Any
from langgraph.types import interrupt
from app.agent.state import PlanState, PlanStatus


def node_prepare_review(state: PlanState) -> dict[str, Any]:
    """节点：生成结构化行程审阅简报，准备进入人机交互挂起状态。"""
    now_dt = datetime.now(UTC)
    itinerary = state.get("current_itinerary")
    report = state.get("constraint_report")

    if not itinerary:
        return {"status": PlanStatus.FAILED, "last_error": "无可用行程进行审阅"}

    day_count = len(itinerary.days)
    total_cost_str = (
        f"{itinerary.budget.planned_total.amount / 100.0:.1f} {itinerary.budget.planned_total.currency}"
        if itinerary.budget
        else "0 CNY"
    )
    status_text = "完美合规" if report and report.passed else "存在部分规则妥协"

    summary = (
        f"[方案就绪] 旅行方案已就绪（共 {day_count} 天行程，预估总花费 {total_cost_str}）。\n"
        f"[规则审计] 状态: {status_text} (违规项: {len(report.violations) if report else 0} 个)。\n"
        f"[提示] 请审阅日程安排。您可以直接点击【确认出游】，或在下方输入修改意见（例如：'第二天下午多安排咖啡馆休息'）。"
    )

    event = {
        "node": "prepare_review",
        "message": "方案已生成，进入【人在回路】挂起等待状态，等待用户确认或提出调整意见。",
        "timestamp": now_dt.isoformat(),
    }

    return {
        "review_summary": summary,
        "status": PlanStatus.AWAITING_REVIEW,
        "audit_events": [event],
        "updated_at": now_dt,
    }


def node_human_interrupt(state: PlanState) -> dict[str, Any]:
    """节点：LangGraph 原生中断点。在此处安全挂起图执行，等待外部输入注入。"""
    # interrupt() 接收展示给用户的信息，并阻塞当前协程/线程
    # 当外部通过 Command(resume=...) 唤醒时，interrupt() 将返回用户传入的指令
    user_input = interrupt({
        "trip_id": state["trip_id"],
        "summary": state.get("review_summary"),
        "itinerary": state.get("current_itinerary"),
    })

    now_dt = datetime.now(UTC)
    action = user_input.get("action", "approve")
    feedback = user_input.get("feedback")

    if action == "approve":
        event = {
            "node": "human_interrupt",
            "message": "用户已批准当前旅行方案，规划流程圆满达成！",
            "timestamp": now_dt.isoformat(),
        }
        return {
            "status": PlanStatus.APPROVED,
            "user_feedback": None,
            "audit_events": [event],
            "updated_at": now_dt,
        }

    # 用户提出修改意见
    event = {
        "node": "human_interrupt",
        "message": f"接收到用户修改意见: '{feedback}'，准备触发动态局部调整。",
        "timestamp": now_dt.isoformat(),
    }
    return {
        "status": PlanStatus.USER_FEEDBACK,
        "user_feedback": feedback,
        "audit_events": [event],
        "updated_at": now_dt,
    }