from datetime import date
from fastapi.testclient import TestClient

from app.domain.replanning import RemovePlaceOp, ReplacePlaceOp
from app.fixtures.loader import load_tokyo_trip_request
from app.main import create_app


def test_dynamic_replanning_preserves_unaffected_days_and_generates_diff() -> None:
    """验证场景：在 3 天行程中，仅替换第 2 天的景点，Day 1 和 Day 3 必须 100% 保持完全不变。"""
    client = TestClient(create_app())

    # 1. 创建旅行并启动 v1 规划
    trip = client.post(
        "/api/v1/trips",
        json=load_tokyo_trip_request().model_dump(mode="json"),
    ).json()
    base_url = f"/api/v1/trips/{trip['id']}"

    client.post(base_url + "/planning-runs")
    v1_plan = client.get(base_url + "/plans/1").json()
    v1_days = v1_plan["itinerary"]["days"]
    assert len(v1_days) == 5

    v1_day1_act_ids = [a["id"] for a in v1_days[0]["activities"]]
    v1_day3_act_ids = [a["id"] for a in v1_days[2]["activities"]]

    # 2. 选取一个有活动的日期进行局部替换测试
    target_idx = next(i for i, d in enumerate(v1_days) if len(d["activities"]) > 0)
    target_day = v1_days[target_idx]["date"]
    old_place_title = v1_days[target_idx]["activities"][0]["title"]

    unaffected_indices = [i for i in range(len(v1_days)) if i != target_idx]
    v1_unaffected_map = {i: [a["id"] for a in v1_days[i]["activities"]] for i in unaffected_indices}

    payload = {
        "base_plan_version": 1,
        "operations": [
            {
                "op": "replace_place",
                "original_place_name": old_place_title,
                "replacement_place_name": "浅草寺",
                "day": target_day,
            }
        ],
    }

    resp = client.post(base_url + "/replanning-runs", json=payload)
    assert resp.status_code == 201
    body = resp.json()

    # 3. 验证版本派生与关系
    assert body["plan"]["version"] == 2
    assert body["plan"]["parent_version"] == 1
    assert body["planning_run"]["result_plan_version"] == 2

    # 4. 验证核心原则：未受波及日期的活动 100% 零扰动
    v2_days = body["plan"]["itinerary"]["days"]
    for i in unaffected_indices:
        v2_act_ids = [a["id"] for a in v2_days[i]["activities"]]
        assert v1_unaffected_map[i] == v2_act_ids, f"第 {i+1} 天未受波及，活动 ID 必须完全一致！"

    # 5. 验证 Diff 报告准确性
    diff = body["diff"]
    assert diff["from_version"] == 1
    assert diff["to_version"] == 2
    assert diff["affected_dates"] == [target_day]
    print(f"\n[Plan Diff 报告概要]: {diff['human_summary']}")