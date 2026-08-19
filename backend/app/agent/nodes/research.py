from datetime import UTC, datetime
from typing import Any

from app.agent.state import PlanState, PlanStatus
from app.infrastructure.composite_facts_factory import CompositeFactsFactory


def node_research_facts(state: PlanState, factory: CompositeFactsFactory) -> dict[str, Any]:
    """节点：调用防腐层获取目标目的地的天气、POI 地点与路线距离矩阵。"""
    request = state["request"]
    planned_at = datetime.now(UTC)

    # 记录审计事件
    event = {
        "node": "research_facts",
        "message": f"正在调研目的地 [{request.destination}] 的真实气象与地点数据...",
        "timestamp": planned_at.isoformat(),
    }

    try:
        # 调用聚合事实工厂 (自动根据经纬度执行国内高德/海外开源双模路由)
        facts = factory.build(request=request, planned_at=planned_at)

        return {
            "places": facts.places,
            "weather_forecast": facts.weather,
            "route_matrix_cells": tuple(facts.route_matrix.cells),
            "exchange_rates": facts.exchange_rates,
            "status": PlanStatus.PLANNING,
            "audit_events": [event],
            "updated_at": planned_at,
        }
    except Exception as exc:
        print(f"\n[node_research_facts error]: {exc}")
        err_event = {
            "node": "research_facts",
            "error": f"多源事实采集失败: {exc}",
            "timestamp": planned_at.isoformat(),
        }
        return {
            "places": (),
            "weather_forecast": (),
            "route_matrix_cells": (),
            "status": PlanStatus.FAILED,
            "last_error": str(exc),
            "audit_events": [event, err_event],
            "updated_at": planned_at,
        }
