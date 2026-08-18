from fastapi import APIRouter
from app.api.v1.feedback import router as feedback_router
from app.api.v1.health import router as health_router
from app.api.v1.manual_edits import router as manual_edits_router
from app.api.v1.planning import router as planning_router
from app.api.v1.plans import router as plans_router
from app.api.v1.trips import router as trips_router
from app.api.v1.agent import router as agent_router
from app.api.v1.replanning import router as replanning_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(trips_router)
api_v1_router.include_router(planning_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(manual_edits_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(replanning_router)

__all__ = [
    "api_v1_router",
    "feedback_router",
    "health_router",
    "manual_edits_router",
    "planning_router",
    "plans_router",
    "trips_router",
    "agent_router",
    "replanning_router",
]
