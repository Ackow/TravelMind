from pydantic import BaseModel, ConfigDict, Field

from app.agent.llm_client import LLMClient
from app.domain.itinerary import Itinerary


class PlanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="为行程起一个吸引人且符合特色的标题")
    overview: str = Field(description="行程总体设计理念与亮点概括（100字左右）")
    daily_highlights: list[str] = Field(description="每天一句话的核心特色亮点")
    change_summary: str = Field(description="相比上一版本的具体调整说明；若是首版则填写'初始规划生成'")


class SummaryGenerator:
    """依据结构化行程事实，生成人类可读的高质量总结文案。"""

    SYSTEM_PROMPT = """
    你是一个文笔优雅、注重事实的旅行顾问。
    你的任务是根据给定的行程数据，提炼出吸引人的旅行标题、亮点介绍和版本变更说明。

    原则：
    1. 文案必须完全契合行程中实际包含的地点和时间，严禁脑补行程中不存在的景点。
    2. 语言简练生动、积极热情。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def generate(self, itinerary: Itinerary, previous_itinerary: Itinerary | None = None) -> PlanSummary:
        days_overview = []
        for d in itinerary.days:
            act_name = [a.title for a in d.activities if a.kind != "transfer"]
            days_overview.append(f"Day {d.date}: 主题【{d.theme}】 包含地点:{','.join(act_name)}")

        user_prompt = f"""
        行程包含 {len(itinerary.days)} 天，总花费 ￥{itinerary.budget.planned_total.amount / 100}: 
        {chr(10).join(days_overview)}
        上一版本情况：{'存在上一版行程，本次为修改调整版' if previous_itinerary else '首版创建'}

        请生成行程标题、亮点与说明：
        """

        response = self._llm.generate_structured(
            schema=PlanSummary,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
        )
        return response.data