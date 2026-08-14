from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.constraints import ConstraintReport


def test_report_rejects_passed_when_error_exists() -> None:
    with pytest.raises(ValidationError):
        ConstraintReport.model_validate(
            {
                "passed": True,
                "violations": [
                    {
                        "id": str(UUID(int=1)),
                        "code": "BUDGET_EXCEEDED",
                        "severity": "error",
                        "day": None,
                        "activity_id": None,
                        "message": "总预算超限",
                        "actual": {"amount": 10001},
                        "expected": {"maximum_amount": 10000},
                        "repair_hint": "删除低优先级付费活动",
                        "rule_version": "1.0.0",
                    }
                ],
                "checked_rule_codes": ["BUDGET_EXCEEDED"],
                "checked_at": datetime(2026, 9, 30, tzinfo=UTC),
                "engine_version": "1.0.0",
            }
        )
