from app.domain.constraints import ConstraintReport
from app.scripts.check_fixture_constraints import main


def test_check_fixture_constraints_prints_valid_report_json(capsys) -> None:
    """示例脚本必须输出能够按 ConstraintReport 回读的纯 JSON。"""
    main()

    report = ConstraintReport.model_validate_json(capsys.readouterr().out)
    assert report.passed is True
    assert report.engine_version == "1.0.0"
