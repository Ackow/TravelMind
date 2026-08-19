from app.eval.evaluator import BatchEvalSummary


def generate_markdown_eval_report(summary: BatchEvalSummary) -> str:
    """将批量评测结果格式化为高可读性的 GitHub Markdown 质量看板。"""
    pass_emoji = "🟢 PASS" if summary.hard_constraint_pass_rate == 100.0 else "🔴 REGRESSION"

    lines = [
        "# 📊 TravelMind Agent 质量评估基准报告 (Eval Benchmark)",
        "",
        f"> **评测结论**：`{pass_emoji}` | **总用例数**：{summary.total_cases} | **完全通过用例**：{summary.passed_cases}/{summary.total_cases}",
        "",
        "## 1. 核心质量指标大盘",
        "",
        "| 评估指标 | 实测结果 | 目标基线 | 状态 |",
        "| :--- | :--- | :--- | :--- |",
        f"| **硬约束合规率 (Hard Constraints)** | `{summary.hard_constraint_pass_rate}%` | 100.0% | {'✅ 达标' if summary.hard_constraint_pass_rate == 100.0 else '❌ 阻塞'} |",
        f"| **预算求和绝对精确率 (Budget Exact)** | `{summary.budget_exact_match_rate}%` | 100.0% | {'✅ 达标' if summary.budget_exact_match_rate == 100.0 else '❌ 阻塞'} |",
        f"| **多源事实可追溯率 (Traceability)** | `{summary.average_traceability_rate}%` | ≥ 95.0% | {'✅ 达标' if summary.average_traceability_rate >= 95.0 else '⚠️ 预警'} |",
        f"| **平均单次规划执行耗时** | `{summary.average_duration_ms} ms` | ≤ 500 ms | {'✅ 优秀' if summary.average_duration_ms <= 500 else '⚠️ 偏高'} |",
        "",
        "## 2. 逐用例明细列表",
        "",
        "| 用例 ID | 场景分类 | 约束通过 | 预算精确 | 事实追溯率 | 耗时 (ms) | 结果 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in summary.detailed_results:
        status_tag = "✅ 正常" if r.passed_hard_constraints and r.budget_exact_match else "❌ 失败"
        lines.append(
            f"| `{r.case_id}` | {r.category} | {'✅' if r.passed_hard_constraints else '❌'} | {'✅' if r.budget_exact_match else '❌'} | {r.traceability_rate * 100:.1f}% | {r.duration_ms} | {status_tag} |"
        )

    return "\n".join(lines)
