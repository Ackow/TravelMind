from pydantic import BaseModel, ConfigDict, Field

from app.agent.llm_client import LLMClient
from app.domain.research import Place, WeatherDay
from app.domain.trip import TripPreferences


class RankedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    place_id: str
    relevance_score: float = Field(ge=0.0, le=1.0, description="0.0 到 1.0 之间的匹配分")
    highlight_reason: str = Field(description="为什么该地点符合用户偏好的简短理由")


class PlaceRankResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ranked_places: list[RankedItem]


class PlaceReranker:
    """结合真实 POI 事实与用户偏好，利用 LLM 进行语义打分与重排序。"""

    SYSTEM_PROMPT = """
    你是一个旅行偏好分析专家。
    根据用户的兴趣、同行者特征和当日天气，对给定的真实地点候选库进行打分排序。

    重要规则：
    1. 绝对不要编造未在候选列表中的地点 ID。
    2. 遇到雨天（降雨概率 > 50% 或室外适宜度差）时，室内场馆得分应高于室外景区。
    3. 必须输出严格的 JSON 格式。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def rerank(
        self,
        places: list[Place],
        preferences: TripPreferences,
        weather: WeatherDay | None = None,
    ) -> list[tuple[Place, float, str]]:
        if not places:
            return []

        place_map = {str(p.id): p for p in places}
        place_descriptions = [
            f"""
            - ID: {p.id} | 名称: {p.name} 
            | 分类: {", ".join(c.value for c in p.categories)} 
            | 室内外: {p.indoor_outdoor.value} | 标签: {",".join(p.tags)}
            """
            for p in places
        ]

        weather_desc = (
            f"""
            天气: {weather.condition.value}，
            降水概率: {weather.rain_probability:.0%}
            """
            if weather and weather.rain_probability is not None
            else f"天气: {weather.condition.value}"
            if weather
            else "天气正常"
        )
        interests_desc = ", ".join(f"{i.value}(权重{i.weight})" for i in preferences.interests)

        user_prompt = f"""
        用户偏好:
        - 兴趣: {interests_desc}
        - 避开: {", ".join(preferences.avoid) or "无"}
        - 节奏: {preferences.pace.value}
        - 当日天气: {weather_desc}

        候选地点列表（共{(len(places))}个）:
        {chr(10).join(place_descriptions)}
        请对候选地点进行偏好匹配打分排序：
        """

        response = self._llm.generate_structured(
            schema=PlaceRankResult,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        # 严格防御性校验：过滤掉 LLM 可能幻觉产生的非法 ID
        results: list[tuple[Place, float, str]] = []
        for item in response.data.ranked_places:
            if item.place_id in place_map:
                results.append(
                    (place_map[item.place_id], item.relevance_score, item.highlight_reason)
                )

            # 若有地点被 LLM 遗漏，以默认分兜底追加在末尾
            ranked_ids = {item.place_id for item in response.data.ranked_places}
            for p in places:
                if str(p.id) not in ranked_ids:
                    results.append((p, 0.5, "常规备选地点"))

            return sorted(results, key=lambda x: x[1], reverse=True)
