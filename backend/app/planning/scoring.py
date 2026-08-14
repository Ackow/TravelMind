from datetime import date

from app.domain.research import (
    IndoorOutdoor,
    OutdoorSuitability,
    Place,
    PlaceCategory,
    WeatherDay,
)
from app.domain.trip import TripRequest
from app.planning.models import CandidateScore
from app.planning.money import MoneyConverter

CATEGORY_KEYWORDS = {
    PlaceCategory.ANIME: "动漫",
    PlaceCategory.FOOD: "美食",
    PlaceCategory.RESTAURANT: "美食",
    PlaceCategory.CAFE: "咖啡",
    PlaceCategory.SHOPPING: "购物",
    PlaceCategory.MUSEUM: "博物馆",
    PlaceCategory.PARK: "公园",
    PlaceCategory.TEMPLE: "寺庙",
    PlaceCategory.SHRINE: "神社",
}


def normalize(value: str) -> str:
    """去除首尾空格和大小写归一化"""
    return value.strip().casefold()


def place_names(place: Place) -> set[str]:
    names = {normalize(place.name)}
    if place.localized_name:
        names.add(normalize(place.localized_name))
    return names


def place_tokens(place: Place) -> set[str]:
    """收集评分时可匹配的稳定关键词。"""
    tokens = place_names(place)
    tokens.update(normalize(tag) for tag in place.tags)
    for category in place.categories:
        tokens.add(normalize(category.value))
        keyword = CATEGORY_KEYWORDS.get(category)
        if keyword:
            tokens.add(normalize(keyword))
    return tokens


def is_hard_excluded(place: Place, request: TripRequest) -> bool:
    excluded = {normalize(name) for name in request.constraints.excluded_place_names}
    return bool(place_names(place) & excluded)


def is_required(place: Place, request: TripRequest) -> bool:
    required = {normalize(name) for name in request.constraints.required_place_names}
    return bool(place_names(place) & required)


def fits_single_place_budget(
    place: Place,
    request: TripRequest,
    converter: MoneyConverter,
) -> bool:
    """硬预算下，单个地点的团体门票不能已经超过整个旅行预算。"""
    if place.admission is None or not request.constraints.budget_is_hard_limit:
        return True

    converted = converter.convert(place.admission, request.display_currency)
    return converted.amount * request.travelers <= request.constraints.total_budget.amount


def is_eligible(
    place: Place,
    request: TripRequest,
    weather: WeatherDay | None,
) -> bool:
    """先执行不能被软评分覆盖的硬过滤。"""
    if is_hard_excluded(place, request):
        return False

    if request.constraints.accessible_only and place.accessible is not True:
        return False

    # poor 天气下先排除纯室外地点，避免明知冲突仍交给修正器处理。
    if (
        weather is not None
        and weather.outdoor_suitability == OutdoorSuitability.POOR
        and place.indoor_outdoor == IndoorOutdoor.OUTDOOR
    ):
        return False

    return True


def score_place(
    *,
    place: Place,
    request: TripRequest,
    weather: WeatherDay | None,
    converter: MoneyConverter,
) -> CandidateScore:
    """计算地点在某一天的分数，并保留人类可读原因。"""

    score = (place.rating or 2.5) * 10
    reasons = [f"评分基础分 {score:.1f}"]
    tokens = place_tokens(place)

    for preference in request.preferences.interests:
        if normalize(preference.value) in tokens:
            bonus = 40 * preference.weight
            score += bonus
            reasons.append(f"匹配兴趣“{preference.value}” +{bonus:.1f}")

    for avoided in request.preferences.avoid:
        if normalize(avoided) in tokens:
            score -= 80
            reasons.append(f"匹配软避开项“{avoided}” -80")

    if weather is not None:
        if weather.outdoor_suitability == OutdoorSuitability.POOR:
            if place.indoor_outdoor == IndoorOutdoor.INDOOR:
                score += 25
                reasons.append("恶劣天气优先室内 +25")
            elif place.indoor_outdoor == IndoorOutdoor.MIXED:
                score -= 30
                reasons.append("恶劣天气降低 mixed 优先级 -30")
        elif (
            weather.outdoor_suitability == OutdoorSuitability.GOOD
            and place.indoor_outdoor == IndoorOutdoor.OUTDOOR
        ):
            score += 10
            reasons.append("好天气适合户外 +10")

    if place.admission is not None:
        converted = converter.convert(
            place.admission,
            request.display_currency,
        )
        group_cost = converted.amount * request.travelers
        budget_amount = max(request.constraints.total_budget.amount, 1)
        budget_share = group_cost / budget_amount
        penalty = min(budget_share * 200, 200)
        score -= penalty
        reasons.append(f"门票成本惩罚 -{penalty:.1f}")

    if is_required(place, request):
        score += 500
        reasons.append("用户必去地点 +500")

    return CandidateScore(
        place_id=place.id,
        score=round(score, 4),
        reasons=tuple(reasons),
    )


def rank_places_for_day(
    *,
    target_date: date,
    places: tuple[Place, ...],
    weather_by_date: dict[date, WeatherDay],
    request: TripRequest,
    converter: MoneyConverter,
    blocked_place_ids: frozenset[str] = frozenset(),
) -> list[CandidateScore]:
    """返回某一天可使用的候选地点，分数相同时按 Place ID 排序。"""

    weather = weather_by_date.get(target_date)
    candidates = [
        score_place(
            place=place,
            request=request,
            weather=weather,
            converter=converter,
        )
        for place in places
        if place.id not in blocked_place_ids
        and is_eligible(place, request, weather)
        and fits_single_place_budget(place, request, converter)
    ]
    return sorted(
        candidates,
        key=lambda item: (-item.score, item.place_id),
    )
