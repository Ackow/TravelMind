from datetime import datetime
import json
from collections.abc import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel
from typing import Any

from app.agent.graph import create_travel_agent_graph
from app.agent.state import PlanStatus
from app.api.dependencies import FactsFactoryDep
from app.domain.trip import TripRequest
from app.infrastructure.composite_facts_factory import CompositeFactsFactory

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class StartPlanningResponse(BaseModel):
    trip_id: str
    status: PlanStatus
    message: str


class ResumePlanningRequest(BaseModel):
    action: str     # "approve" | "modify"
    feedback: str | None = None


@router.post("/trips/plan/stream", summary="流式启动Agent规划")
async def stream_trip_planning(
    request: TripRequest,
    factory: FactsFactoryDep,
) -> StreamingResponse:
    """启动 Agent 规划流程并通过 SSE 实时推送执行日志与状态。"""
    if not isinstance(factory, CompositeFactsFactory):
        # 统一转为聚合工厂
        factory = CompositeFactsFactory()

    graph = create_travel_agent_graph(facts_factory=factory)
    trip_id = f"trip_{request.destination}_{int(datetime.now().timestamp())}"

    initial_state = {
        "trip_id": trip_id,
        "request": request,
        "destination": request.destination,
        "repair_attempts": 0,
        "max_repair_attempts": 3,
        "applied_repairs": [],
        "status": PlanStatus.INIT,
        "audit_events": [],
    }

    config = {"configurable": {"thread_id": trip_id}}

    async def event_generator() -> AsyncGenerator[str, None]:
        # 逐步流式产出 LangGraph 的节点输出事件
        for event in graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_output in event.items():
                payload = {
                    "node": node_name,
                    "status": node_output.get("status"),
                    "events": node_output.get("audit_events", []),
                    "summary": node_output.get("review_summary"),
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/trips/{trip_id}/resume", summary="人在回路：恢复挂起的 Agent")
async def resume_trip_planning(
    trip_id: str,
    resume_req: ResumePlanningRequest,
    factory: FactsFactoryDep,
) -> dict[str, Any]:
    """人在回路：用户完成审阅后，注入批准或修改指令，唤醒挂起的 Agent。"""
    if not isinstance(factory, CompositeFactsFactory):
        factory = CompositeFactsFactory()

    graph = create_travel_agent_graph(facts_factory=factory)
    config = {"configurable": {"thread_id": trip_id}}

    # 通过 Command(resume=...) 唤醒 interrupt 节点
    result = graph.invoke(
        Command(resume={"action": resume_req.action, "feedback": resume_req.feedback}),
        config=config,
    )

    return {
        "trip_id": trip_id,
        "status": result.get("status"),
        "current_itinerary": result.get("current_itinerary"),
        "audit_events": result.get("audit_events", []),
    }