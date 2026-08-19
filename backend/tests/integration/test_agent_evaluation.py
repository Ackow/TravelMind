from app.eval.dataset import get_golden_dataset
from app.eval.evaluator import AgentEvaluator
from app.eval.reporter import generate_markdown_eval_report
from app.infrastructure.tokyo_facts_factory import TokyoFactsFactory


def test_agent_evaluation_benchmark_suite():
    """自动化运行黄金评测基准，要求硬约束合规率与预算求和精度必须达到 100%。"""
    dataset = get_golden_dataset()
    evaluator = AgentEvaluator(facts_factory=TokyoFactsFactory())

    summary = evaluator.run_benchmark(dataset)
    report_md = generate_markdown_eval_report(summary)

    # 门禁断言：硬约束合规率与预算精度不允许出现负向劣化
    assert summary.hard_constraint_pass_rate == 100.0, (
        f"硬约束合规率低于 100%: {summary.hard_constraint_pass_rate}%"
    )
    assert summary.budget_exact_match_rate == 100.0, (
        f"预算求和精度低于 100%: {summary.budget_exact_match_rate}%"
    )
    assert summary.average_traceability_rate >= 90.0, (
        f"事实追溯率低于基线: {summary.average_traceability_rate}%"
    )
