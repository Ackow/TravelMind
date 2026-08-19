from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.llm_client import LLMClient
from app.domain.common import Money
from app.domain.trip import TripRequest


class SetBudgetOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["set_budget"]
    total_budget: Money
    budget_is_hard_limit: bool = True
    reason: str


class SetMaxWalkingOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["set_max_walking"]
    meters_per_day: int = Field(ge=500, le=50000)
    reason: str


class AdddRequiredPlaceOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["add_required_place"]
    place_name: str
    preferred_date: date | None = None
    reason: str


class AddExcludedPlaceOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["add_excluded_place"]
    place_name: str
    reason: str


class SetPaceOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["set_pace"]
    pace: Literal["relaxed", "balanced", "packed"]
    reason: str


FeedbackOp = Annotated[
    SetBudgetOp | SetMaxWalkingOp | AdddRequiredPlaceOp | AddExcludedPlaceOp | SetPaceOp,
    Field(discriminator="op"),
]


class ParsedFeedback(BaseModel):
    """LLM 输出的强类型反馈解析结果。"""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="对用户调整意图的简要中文概述")
    operations: list[FeedbackOp] = Field(description="解析出的原子变更指令列表")
    affected_day_indices: list[int] = Field(
        default_factory=list,
        description="受影响的行程天数序号 (从 1 开始)，若影响全局则传空列表",
    )
    requires_clarification: bool = Field(
        description="如果用户的指令完全模糊、无法提取任何明确操作或相互矛盾，则为 True"
    )
    clarification_question: str | None = Field(
        default=None,
        description="当 requires_clarification 为 True 时，向用户提出的具体追问建议",
    )


class FeedbackParser:
    """负责将自然语言反馈转化为可执行的领域约束操作。"""

    SYSTEM_PROMPT = """
    你是一个专业的旅行规划助手。你的任务是将用户的自然语言修改反馈解析为严格的结构化操作指令列表。

    规则：
    1. 只能提取用户明确要求或强烈暗示的修改，不要擅自增加未提及的约束。
    2. 距离转换：1 公里 = 1000 米。
    3. 金额转换：解析为整数分 (例如 5000 元 -> amount: 500000, currency: 'CNY')。
    4. 若用户输入与旅行规划完全无关的闲聊，将 requires_clarification 设为 True，并生成温和的澄清追问。
    5. 必须返回符合 JSON Schema 的严格结构。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def parse(self, message: str, trip_request: TripRequest) -> ParsedFeedback:
        user_prompt = f"""
        当前旅游背景：
        - 目的地：{trip_request.destination}
        - 日期范围：{trip_request.date_range.start_date} 至 {trip_request.date_range.end_date}
        - 同行人数：{trip_request.travelers}
        - 当前预算：{trip_request.constraints.total_budget.amount / 100}
        - 当前最大步行：{trip_request.constraints.max_walking_meters_per_day} 米/天
        
        用户反馈文本：“{message}”

        请提取结构化变更操作：
        """
        response = self._llm.generate_structured(
            schema=ParsedFeedback,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        return response.data
