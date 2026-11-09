"""Unit tests for morning workflow, human approval, and fake sender delivery."""

from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from agent_api.database.db import get_connection, init_db
from agent_api.main import app
from agent_api.services.morning_workflow import run_morning_workflow
from agent_api.services.notification_service import (
    FakeSender,
    approve_draft,
    dispatch_outbox_for_draft,
    get_draft,
    list_drafts,
    list_messages,
    reject_draft,
)


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Provide a fresh isolated SQLite database for each test."""
    db_file = str(tmp_path / "test_schoolops.db")
    monkeypatch.setattr("agent_api.config.DB_PATH", db_file)
    monkeypatch.setattr("agent_api.database.db.DB_PATH", db_file)
    init_db(db_file)
    return db_file


def mock_adverse_weather(*args, **kwargs):
    # Simulate heavy rainfall (35 mm) triggering route delay & indoor event
    return {
        "status": "ok",
        "data": {
            "date": "2026-11-10",
            "max_temp": 28.0,
            "rain_probability_max": 80,
            "rain_sum": 35.0,
            "hourly_rain": [],
        },
    }


def mock_safe_weather(*args, **kwargs):
    return {
        "status": "ok",
        "data": {
            "date": "2026-11-10",
            "max_temp": 28.0,
            "rain_probability_max": 10,
            "rain_sum": 0.0,
            "hourly_rain": [],
        },
    }


def mock_safe_aqi(*args, **kwargs):
    return {
        "status": "ok",
        "data": {
            "date": "2026-11-10",
            "us_aqi": 85,
            "pm2_5": 20.0,
        },
    }


# ==========================================
# Gate Requirements Tests
# ==========================================

@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_job_twice_idempotency_same_draft_count(mock_aq, mock_fc, test_db):
    """Gate requirement: Running the job twice on the same date produces the exact same draft count."""
    run1 = run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    drafts1 = list_drafts(db_path=test_db)
    count1 = len(drafts1)
    assert count1 > 0

    run2 = run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    drafts2 = list_drafts(db_path=test_db)
    count2 = len(drafts2)

    assert count1 == count2
    assert [d["idempotency_key"] for d in drafts1] == [d["idempotency_key"] for d in drafts2]


@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_unapproved_draft_cannot_be_sent_outbox_empty(mock_aq, mock_fc, test_db):
    """Gate requirement: Unapproved drafts cannot be sent; outbox remains completely empty."""
    run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    drafts = list_drafts(db_path=test_db)

    # All generated drafts must be PENDING
    assert len(drafts) > 0
    assert all(d["status"] == "PENDING" for d in drafts)

    # Outbox must be strictly empty
    messages = list_messages(db_path=test_db)
    assert len(messages) == 0


@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_approve_delivers_messages_and_double_approve_no_duplicates(mock_aq, mock_fc, test_db):
    """Gate requirement: Approving a draft delivers messages; double approve is a no-op with no duplicate sends."""
    run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    route_drafts = list_drafts(status="PENDING", db_path=test_db)
    target_draft = next(d for d in route_drafts if d["type"] == "ROUTE_DELAY")

    # 100% reliable sender
    perfect_sender = FakeSender(fail_rate=0.0)

    # First approve
    res1 = approve_draft(target_draft["id"], sender=perfect_sender, db_path=test_db)
    assert res1["status"] == "approved"
    assert res1["dispatched"]["delivered"] > 0

    # Verify messages in outbox are marked SENT
    sent_messages = list_messages(draft_id=target_draft["id"], db_path=test_db)
    assert len(sent_messages) > 0
    assert all(m["status"] == "SENT" for m in sent_messages)
    original_sent_count = len(sent_messages)

    # Second approve call (double approval)
    res2 = approve_draft(target_draft["id"], sender=perfect_sender, db_path=test_db)
    assert res2["status"] == "already_approved"

    # Assert no duplicate messages were queued or sent
    messages_after = list_messages(draft_id=target_draft["id"], db_path=test_db)
    assert len(messages_after) == original_sent_count


@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_reject_sends_no_messages(mock_aq, mock_fc, test_db):
    """Gate requirement: Rejecting a draft transitions to REJECTED and sends zero messages."""
    run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    drafts = list_drafts(status="PENDING", db_path=test_db)
    target = drafts[0]

    reject_res = reject_draft(target["id"], db_path=test_db)
    assert reject_res["status"] == "rejected"

    updated = get_draft(target["id"], db_path=test_db)
    assert updated["status"] == "REJECTED"

    # Outbox remains empty
    assert len(list_messages(draft_id=target["id"], db_path=test_db)) == 0


@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_sender_forced_to_fail_and_retries_up_to_3(mock_aq, mock_fc, test_db):
    """Gate requirement: Sender forced to fail retries up to 3 times with no duplicate deliveries."""
    run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    route_drafts = list_drafts(status="PENDING", db_path=test_db)
    target = next(d for d in route_drafts if d["type"] == "ROUTE_DELAY")

    # 1. Force failure on first attempt
    failing_sender = FakeSender(fail_rate=1.0)
    approve_draft(target["id"], sender=failing_sender, db_path=test_db)

    msgs = list_messages(draft_id=target["id"], db_path=test_db)
    assert all(m["status"] == "FAILED" for m in msgs)
    assert all(m["attempts"] == 1 for m in msgs)

    # 2. Retry attempt 2 (still failing)
    dispatch_outbox_for_draft(target["id"], sender=failing_sender, max_attempts=3, db_path=test_db)
    msgs = list_messages(draft_id=target["id"], db_path=test_db)
    assert all(m["status"] == "FAILED" for m in msgs)
    assert all(m["attempts"] == 2 for m in msgs)

    # 3. Retry attempt 3 with working sender (should succeed)
    working_sender = FakeSender(fail_rate=0.0)
    dispatch_outbox_for_draft(target["id"], sender=working_sender, max_attempts=3, db_path=test_db)
    msgs = list_messages(draft_id=target["id"], db_path=test_db)
    assert all(m["status"] == "SENT" for m in msgs)
    assert all(m["attempts"] == 3 for m in msgs)

    # 4. Attempt 4 must NOT touch SENT messages
    dispatch_outbox_for_draft(target["id"], sender=working_sender, max_attempts=3, db_path=test_db)
    msgs = list_messages(draft_id=target["id"], db_path=test_db)
    assert all(m["attempts"] == 3 for m in msgs)


@patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_safe_weather)
@patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi)
def test_all_clear_day_creates_no_parent_drafts(mock_aq, mock_fc, test_db):
    """Gate requirement: ALL_CLEAR day creates zero parent drafts."""
    res = run_morning_workflow(run_date="2026-11-10", db_path=test_db)
    assert res["alerts_count"] == 0

    drafts = list_drafts(db_path=test_db)
    assert len(drafts) == 1
    assert drafts[0]["type"] == "ALL_CLEAR"
    assert drafts[0]["status"] == "ALL_CLEAR"

    # Zero parent drafts created
    parent_drafts = [d for d in drafts if d["type"] in ("ROUTE_DELAY", "EVENT_OUTDOOR")]
    assert len(parent_drafts) == 0

    # Zero outbox messages
    assert len(list_messages(db_path=test_db)) == 0


def test_fastapi_workflow_endpoints(test_db):
    """Test REST API endpoints for morning job and approval workflow."""
    client = TestClient(app)

    # Trigger job
    with patch("agent_api.services.morning_workflow.get_forecast", side_effect=mock_adverse_weather):
        with patch("agent_api.services.morning_workflow.get_air_quality", side_effect=mock_safe_aqi):
            resp = client.post("/jobs/morning/run", json={"date": "2026-11-10"})
            assert resp.status_code == 200

    # View drafts
    resp_drafts = client.get("/drafts")
    assert resp_drafts.status_code == 200
    drafts = resp_drafts.json()
    assert len(drafts) > 0

    target = drafts[0]
    # Patch note
    patch_resp = client.patch(
        f"/drafts/{target['id']}",
        json={"principal_note": "Reviewed and approved by Principal"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["principal_note"] == "Reviewed and approved by Principal"

    # Approve
    approve_resp = client.post(f"/drafts/{target['id']}/approve")
    assert approve_resp.status_code == 200

    # View /messages
    msg_resp = client.get("/messages")
    assert msg_resp.status_code == 200

