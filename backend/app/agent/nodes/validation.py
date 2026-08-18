from datetime import UTC, datetime
from typing import Any
from app.agent.state import PlanState, PlanStatus
from app.constraints import create_default_engine
from app.constraints.context import ConstraintContext


def node_check_constraints(state: PlanState) -> dict[str, Any]:
    """节点：调用确定性约束引擎，毫秒级审核行程中的闭馆、超时、雨天与预算合规性。"""
    now_dt = datetime.now(UTC)
    itinerary = state.get("current_itinerary")
    if not itinerary:
        return {"status": PlanStatus.FAILED, "last_error": "无可用行程方案进行约束检查"}

    request = state["request"]
    places = state.get("places", ())
    engine = create_default_engine()
    context = ConstraintContext(
        request=request,
        places_by_id={p.id: p for p in places},
        checked_at=now_dt,
    )

    report = engine.check(itinerary, context)

    passed_text = "全部通过" if report.passed else f"发现 {len(report.violations)} 处违规项"
    event = {
        "node": "check_constraints",
        "message": f"约束引擎审核完成: {passed_text} (违规数: {len(report.violations)})",
        "violations": [v.message for v in report.violations],
        "timestamp": now_dt.isoformat(),
    }

    return {
        "constraint_report": report,
        "audit_events": [event],
        "updated_at": now_dt,
    }