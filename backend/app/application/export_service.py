from datetime import UTC, datetime
from uuid import UUID

from app.application.errors import ApplicationError
from app.application.repository import TravelRepository
from app.domain.itinerary import ActivityKind


class ExportService:
    """旅行行程方案导出服务，支持生成结构化 Markdown 路书。"""

    def __init__(self, repository: TravelRepository) -> None:
        self._repo = repository

    def export_to_markdown(self, trip_id: UUID, version: int | None = None) -> str:
        """将指定旅行的计划版本渲染为 Markdown 文本。"""
        trip = self._repo.get_trip(trip_id)
        if trip is None:
            raise ApplicationError("TRIP_NOT_FOUND", "旅行不存在", 404)

        target_version = version or trip.current_plan_version or 1
        plan = self._repo.get_plan(trip_id, target_version)
        if plan is None:
            raise ApplicationError("PLAN_NOT_FOUND", f"计划版本 v{target_version} 不存在", 404)

        itinerary = plan.itinerary
        req = trip.request

        # 构建头部元数据
        lines = [
            f"# ✈️ {req.destination} 旅行路书方案 (v{plan.version})",
            "",
            "> 📌 **TravelMind 智能规划中枢生成** | 方案状态：`已确立` | 生成时间："
            + datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            "",
            "## 1. 旅行概览",
            "",
            f"- **目的地**：{req.destination} ({req.destination_timezone})",
            f"- **行程日期**：{req.date_range.start_date} 至 {req.date_range.end_date} (共 {len(itinerary.days)} 天)",
            f"- **出游人数**：{req.travelers} 人 | **旅行节奏**：{req.preferences.pace.value}",
            f"- **总预算规划**：{itinerary.budget.planned_total.amount / 100.0:.2f} {itinerary.budget.planned_total.currency} (硬上限: {req.constraints.total_budget.amount / 100.0:.2f} {req.constraints.total_budget.currency})",
            "",
            "---",
            "",
            "## 2. 逐日详细行程表",
            "",
        ]

        for day in itinerary.days:
            stats = day.statistics
            lines.extend(
                [
                    f"### 📅 第 {day.day_number} 天 ({day.date})",
                    f"> **当日概况**：安排活动 `{stats.activity_count}` 个 | 步行预计 `{stats.walking_meters / 1000.0:.1f} km` | 通勤耗时 `{stats.transfer_minutes} 分钟` | 当日花费 `{stats.estimated_cost.amount / 100.0:.1f} {stats.estimated_cost.currency}`",
                    "",
                    "| 时间 | 类型 | 活动 / 交通安排 | 地点 / 区域 | 预计花费 | 备注 |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )

            for act in day.activities:
                time_range = f"{act.start_at.strftime('%H:%M')} ~ {act.end_at.strftime('%H:%M')}"
                kind_icon = (
                    "🏛️ 游览"
                    if act.kind == ActivityKind.VISIT
                    else ("🍜 餐饮" if act.kind == ActivityKind.MEAL else "🚶 转场")
                )
                cost_str = (
                    f"{act.estimated_cost.amount / 100.0:.1f} {act.estimated_cost.currency}"
                    if act.estimated_cost
                    else "免费"
                )
                location_str = act.title
                notes_str = ", ".join(act.notes) if act.notes else "-"
                lines.append(
                    f"| {time_range} | {kind_icon} | **{act.title}** | {location_str} | {cost_str} | {notes_str} |"
                )

            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 3. 费用预算明细汇总",
                "",
                "| 支出类别 | 预估金额 | 币种 |",
                "| :--- | :--- | :--- |",
            ]
        )
        for cat, amount in itinerary.budget.totals_by_category.items():
            cat_name = cat.value if hasattr(cat, "value") else str(cat)
            lines.append(f"| {cat_name} | {amount.amount / 100.0:.2f} | {amount.currency} |")

        lines.extend(
            [
                f"| **总计支出** | **{itinerary.budget.planned_total.amount / 100.0:.2f}** | **{itinerary.budget.planned_total.currency}** |",
                "",
                "---",
                "",
                "## 4. 出行前安全与注意事项",
                "",
                "- 🛂 **证件与出入境**：请提前确认护照有效期（建议在 6 个月以上）与目的地签证；",
                "- ⚡ **电源与网络**：请准备目的地标准插头转换器与随身 Wi-Fi 或国际漫游流量；",
                "- 🏥 **旅行保险**：建议出游前购买覆盖医疗与行李延误的境外/境内旅游意外险；",
                "- 🌦️ **天气应变**：若遇极端降雨或闭馆，TravelMind 支持在网页端一键触发【动态重规划】自愈替换方案。",
            ]
        )

        return "\n".join(lines)
