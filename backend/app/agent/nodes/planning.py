from datetime import UTC, datetime
from typing import Any
from app.agent.state import PlanState, PlanStatus
from app.domain.research import RouteMatrix
from app.planning.planner import build_itinerary
from app.planning.models import PlanningFacts



def node_build_candidate(state: PlanState) -> dict[str, Any]:
    """节点：调用确定性规划算法生成初版候选行程方案。"""
    now_dt = datetime.now(UTC)
    request = state["request"]
    places = state.get("places")
    if not places:
        from app.fixtures.loader import load_tokyo_places
        places = tuple(load_tokyo_places())

    weather = state.get("weather_forecast")
    if not weather:
        from app.fixtures.loader import load_tokyo_weather
        weather = tuple(load_tokyo_weather())

    cells = state.get("route_matrix_cells")
    if not cells:
        from app.fixtures.loader import load_tokyo_route_matrix
        route_matrix = load_tokyo_route_matrix()
    else:
        from app.domain.common import DataQuality, SourceRef
        source = SourceRef(
            provider="composite",
            source_id="agent-matrix",
            fetched_at=now_dt,
            data_quality=DataQuality.VERIFIED,
        )
        route_matrix = RouteMatrix(cells=list(cells), source=source)

    facts = PlanningFacts(
        request=request,
        places=tuple(places),
        weather=tuple(weather),
        route_matrix=route_matrix,
        exchange_rates={},
        planned_at=now_dt,
    )

    event = {
        "node": "build_candidate",
        "message": "已通过确定性图优化算法生成初版行程草案，准备进行规则合规审核。",
        "timestamp": now_dt.isoformat(),
    }

    try:
        candidate = build_itinerary(facts)
        return {
            "current_itinerary": candidate,
            "status": PlanStatus.VALIDATING,
            "audit_events": [event],
            "updated_at": now_dt,
        }
    except Exception as exc:
        return {
            "status": PlanStatus.FAILED,
            "last_error": f"行程规划生成失败: {exc}",
            "audit_events": [event, {"node": "build_candidate", "error": str(exc), "timestamp": now_dt.isoformat()}],
            "updated_at": now_dt,
        }