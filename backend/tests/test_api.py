"""API 层测试：健康检查、求解往返、422 校验错误定位。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def sample_payload():
    return {
        "events": [
            {"id": "A", "device": "M1", "seq": 1, "observed": 1, "window": {"lo": 1, "hi": 4}},
            {"id": "B", "device": "M1", "seq": 2, "observed": 2, "window": {"lo": 1, "hi": 4}},
            {"id": "C", "device": "M2", "seq": 1, "observed": 1, "window": {"lo": 1, "hi": 4}},
            {"id": "D", "device": "M2", "seq": 2, "observed": 2, "window": {"lo": 1, "hi": 4}},
        ],
        "precedences": [],
    }


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_solve_happy_path_multiple():
    res = client.post("/api/solve", json=sample_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "multiple"
    assert body["cost"] == 4
    assert [t["order"] for t in body["timelines"]] == [
        ["A", "B", "C", "D"],
        ["A", "C", "B", "D"],
    ]


def test_solve_cycle_infeasible():
    payload = sample_payload()
    payload["precedences"] = [{"before": "A", "after": "B"}, {"before": "B", "after": "A"}]
    res = client.post("/api/solve", json=payload)
    assert res.status_code == 200
    assert res.json() == {"status": "infeasible", "timelines": []}


def _locs(res):
    assert res.status_code == 422
    return [e["loc"] for e in res.json()["detail"]]


def test_too_few_events():
    payload = sample_payload()
    payload["events"] = payload["events"][:3]
    res = client.post("/api/solve", json=payload)
    assert "events" in _locs(res)


def test_too_many_events():
    payload = sample_payload()
    payload["events"] = [
        {"id": chr(ord("A") + i), "device": "M1", "seq": i + 1, "observed": 1,
         "window": {"lo": 1, "hi": 21}}
        for i in range(21)
    ]
    res = client.post("/api/solve", json=payload)
    assert "events" in _locs(res)


def test_bad_id_format():
    payload = sample_payload()
    payload["events"][0]["id"] = "a"
    res = client.post("/api/solve", json=payload)
    assert "events[0].id" in _locs(res)


def test_duplicate_id():
    payload = sample_payload()
    payload["events"][1]["id"] = "A"
    res = client.post("/api/solve", json=payload)
    assert "events[1].id" in _locs(res)


def test_duplicate_device_seq():
    payload = sample_payload()
    payload["events"][1]["seq"] = 1  # 与 events[0] 同为 M1#1
    res = client.post("/api/solve", json=payload)
    assert "events[1].seq" in _locs(res)


def test_observed_out_of_range():
    payload = sample_payload()
    payload["events"][2]["observed"] = 21
    res = client.post("/api/solve", json=payload)
    assert "events[2].observed" in _locs(res)


def test_window_hi_out_of_range():
    payload = sample_payload()
    payload["events"][0]["window"]["hi"] = 5  # n=4，上界越界
    res = client.post("/api/solve", json=payload)
    assert "events[0].window.hi" in _locs(res)


def test_window_lo_out_of_range():
    payload = sample_payload()
    payload["events"][0]["window"]["lo"] = 0
    res = client.post("/api/solve", json=payload)
    assert "events[0].window.lo" in _locs(res)


def test_window_inverted():
    payload = sample_payload()
    payload["events"][1]["window"] = {"lo": 3, "hi": 2}
    res = client.post("/api/solve", json=payload)
    assert "events[1].window" in _locs(res)


def test_precedence_unknown_reference():
    payload = sample_payload()
    payload["precedences"] = [{"before": "A", "after": "Z"}]
    res = client.post("/api/solve", json=payload)
    assert "precedences[0].after" in _locs(res)


def test_precedence_self_loop():
    payload = sample_payload()
    payload["precedences"] = [{"before": "A", "after": "A"}]
    res = client.post("/api/solve", json=payload)
    assert "precedences[0]" in _locs(res)


def test_precedence_duplicate():
    payload = sample_payload()
    payload["precedences"] = [
        {"before": "A", "after": "C"},
        {"before": "A", "after": "C"},
    ]
    res = client.post("/api/solve", json=payload)
    assert "precedences[1]" in _locs(res)


def test_malformed_json():
    res = client.post(
        "/api/solve", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"] == "body"
