from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.llm_client import LLMClient
from app.domain.constraints import ConstraintViolation
from app.domain.itinerary import DayPlan


class RepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal[
        "swap_activities", "advance_start_time", "remove_activity", "shorten_duration"
    ]
    target_activity_title: str
    secondary_activity_title: str | None = None
    minutes_adjustment: int | None = None
    rationale: str = Field(description="提议此修复动作的原因")


class RepairProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestions: list[RepairAction]


class RepairProposer:
    """根据约束检查失败报告，提议针对性的行程调整动作。"""

    SYSTEM_PROMPT = """
    你是一个行程调度排期专家。
    当行程出现时间冲突、闭馆或步行过长时，提议最优雅的局部调整动作。
    动作选项：
    - swap_activities: 交换同一天内两个活动的先后顺序
    - advance_start_time: 提早某个活动的开始时间
    - shorten_duration: 缩短某个停留时间过长的活动
    - remove_activity: 移除次要景点（最后手段）
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def propose(
        self, violations: list[ConstraintViolation], day_plan: DayPlan
    ) -> list[RepairAction]:
        if not violations:
            return []

        v_texts = [
            f"- 错误码: {v.code}, 信息: {v.message}, 修复提示: {v.repair_hint}" for v in violations
        ]
        act_texts = [f"- {a.title} ({a.start_at} 至 {a.end_at})" for a in day_plan.activities]

        user_prompt = f"""
        当日活动安排 ({day_plan.date})：{chr(10).join(act_texts)}
        发现的约束冲突：{chr(10).join(v_texts)}

        请提议修复动作：
        """

        response = self._llm.generate_structured(
            schema=RepairProposal,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        return response.data.suggestions
