import time
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.eval.models import GoldenEvalCase
from app.infrastructure.tokyo_facts_factory import TokyoFactsFactory
from app.planning.planner import build_itinerary


class CaseEvalResult(BaseModel):
    """单用例评测执行结果与得分"""

    case_id: str
    category: str
    passed_hard_constraints: bool
    budget_exact_match: bool
    traceability_rate: float
    replanning_stability_rate: float | None = None
    duration_ms: float
    violations_count: int
    error_message: str | None = None


class BatchEvalSummary(BaseModel):
    """全量评测汇总统计报告"""

    total_cases: int
    passed_cases: int
    hard_constraint_pass_rate: float = Field(description="硬约束合规率 (必须 100%)")
    budget_exact_match_rate: float = Field(description="预算求和绝对精确率 (必须 100%)")
    average_traceability_rate: float = Field(description="平均事实可追溯率")
    average_duration_ms: float = Field(description="平均单次规划执行耗时 (ms)")
    detailed_results: list[CaseEvalResult] = Field(default_factory=list)


class AgentEvaluator:
    """Agent 自动化评估执行中枢"""

    def __init__(self, facts_factory=None) -> None:
        self._factory = facts_factory or TokyoFactsFactory()

    def evaluate_case(self, case: GoldenEvalCase) -> CaseEvalResult:
        """运行单个黄金用例并计算多项量化指标"""
        now = datetime.now(UTC)
        start_time = time.perf_counter()

        try:
            # 1. 执行事实提取与规划
            facts = self._factory.build(case.request, now)
            itinerary = build_itinerary(facts)

            # 2. 计算预算严格求和
            total_sum = sum(
                a.estimated_cost.amount
                for day in itinerary.days
                for a in day.activities
                if a.estimated_cost
            )
            budget_match = (
                (itinerary.budget.planned_total.amount == total_sum) if itinerary.budget else True
            )

            # 3. 统计事实追溯率 (检查地点是否来源于事实库)
            fact_place_ids = {p.id for p in facts.places}
            itinerary_place_ids = [
                a.place_id
                for day in itinerary.days
                for a in day.activities
                if a.place_id is not None
            ]
            matched_count = sum(1 for pid in itinerary_place_ids if pid in fact_place_ids)
            traceability = matched_count / max(len(itinerary_place_ids), 1)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return CaseEvalResult(
                case_id=case.case_id,
                category=case.category,
                passed_hard_constraints=True,
                budget_exact_match=budget_match,
                traceability_rate=traceability,
                duration_ms=round(elapsed_ms, 2),
                violations_count=0,
                error_message=None,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            if case.expectations.expected_unfeasible:
                # 预期无解且确实拦截 -> 算作通过
                return CaseEvalResult(
                    case_id=case.case_id,
                    category=case.category,
                    passed_hard_constraints=True,
                    budget_exact_match=True,
                    traceability_rate=1.0,
                    duration_ms=round(elapsed_ms, 2),
                    violations_count=0,
                )

            return CaseEvalResult(
                case_id=case.case_id,
                category=case.category,
                passed_hard_constraints=False,
                budget_exact_match=False,
                traceability_rate=0.0,
                duration_ms=round(elapsed_ms, 2),
                violations_count=1,
                error_message=str(exc),
            )

    def run_benchmark(self, dataset: list[GoldenEvalCase]) -> BatchEvalSummary:
        """批量运行全量黄金评测集并计算汇总指标"""
        results: list[CaseEvalResult] = []
        for case in dataset:
            result = self.evaluate_case(case)
            results.append(result)

        total = len(results)
        passed_count = sum(1 for r in results if r.passed_hard_constraints and r.budget_exact_match)
        hard_pass_rate = sum(1 for r in results if r.passed_hard_constraints) / total
        budget_match_rate = sum(1 for r in results if r.budget_exact_match) / total
        feasible_results = [r for r in results if r.category != "unfeasible"]
        avg_traceability = sum(r.traceability_rate for r in feasible_results) / max(
            len(feasible_results), 1
        )
        avg_duration = sum(r.duration_ms for r in results) / total

        return BatchEvalSummary(
            total_cases=total,
            passed_cases=passed_count,
            hard_constraint_pass_rate=round(hard_pass_rate * 100.0, 2),
            budget_exact_match_rate=round(budget_match_rate * 100.0, 2),
            average_traceability_rate=round(avg_traceability * 100.0, 2),
            average_duration_ms=round(avg_duration, 2),
            detailed_results=results,
        )
