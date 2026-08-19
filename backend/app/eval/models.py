from pydantic import BaseModel, Field

from app.domain.trip import TripRequest


class EvalExpectation(BaseModel):
    """评测用例预期达标断言标准"""

    must_pass_constraints: bool = Field(default=True, description="硬约束是否必须 100% 全部通过")
    max_days: int | None = Field(default=None, description="期望行程天数")
    max_budget_amount: int | None = Field(default=None, description="总预算金额上限")
    budget_currency: str = Field(default="CNY")
    expected_activity_types: list[str] = Field(
        default_factory=list, description="必须包含的活动类型"
    )
    expected_unfeasible: bool = Field(
        default=False, description="是否预期为无解需求（需要系统明确拒识）"
    )


class GoldenEvalCase(BaseModel):
    """黄金评测案例定义"""

    case_id: str = Field(description="用例唯一标识，如 TC_001")
    category: str = Field(
        description="用例分类：standard, budget_stress, weather_stress, closure_stress, replanning"
    )
    title: str = Field(description="用例场景标题")
    description: str = Field(description="用例业务背景说明")
    request: TripRequest = Field(description="旅行请求输入")
    feedback: str | None = Field(default=None, description="模拟后续追加的用户自然语言反馈")
    expectations: EvalExpectation = Field(description="预期校验标准")
