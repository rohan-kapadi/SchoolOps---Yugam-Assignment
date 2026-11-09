"""Notification service for drafting parent messages, human approval, and safe fake sending."""

from datetime import datetime, timezone
import random
from typing import Any
import httpx

from agent_api.config import SENDER_FAIL_RATE
from agent_api.database.db import db_session, get_connection
from agent_api.tools.school_tools import get_events, get_route, get_students

MAX_SEND_ATTEMPTS = 3


class FakeSender:
    """Injectable fake WhatsApp / SMS sender simulating real network delivery."""

    def __init__(self, fail_rate: float = SENDER_FAIL_RATE, rng: random.Random | None = None) -> None:
        self.fail_rate = fail_rate
        self.rng = rng or random.Random()
        self.sent_log: list[dict[str, Any]] = []

    def send(self, recipient_id: str, message_en: str, message_hi: str) -> bool:
        """Attempt to deliver a bilingual notification. Returns True on success, False on failure."""
        roll = self.rng.random()
        success = roll >= self.fail_rate

        self.sent_log.append({
            "recipient_id": recipient_id,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return success


# Default global sender instance
default_sender = FakeSender()


def get_draft(draft_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Fetch a single draft by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,)).fetchone()
        return dict(row) if row else None


def list_drafts(
    status: str | None = None,
    run_date: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """List all drafts with optional status and date filters."""
    query = "SELECT * FROM drafts WHERE 1=1"
    params: list[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if run_date:
        query += " AND date = ?"
        params.append(run_date)
    query += " ORDER BY id ASC;"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_draft(
    draft_id: int,
    summary: str | None = None,
    principal_note: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any] | None:
    """Update draft text or principal note (only while PENDING)."""
    with db_session(db_path) as conn:
        existing = conn.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,)).fetchone()
        if not existing:
            return None
        if existing["status"] != "PENDING":
            raise ValueError(f"Cannot edit draft {draft_id} with status '{existing['status']}'. Must be PENDING.")

        new_summary = summary if summary is not None else existing["summary"]
        new_note = principal_note if principal_note is not None else existing["principal_note"]

        conn.execute(
            """
            UPDATE drafts
            SET summary = ?, principal_note = ?, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (new_summary, new_note, draft_id),
        )
        updated = conn.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,)).fetchone()
        return dict(updated) if updated else None


def approve_draft(
    draft_id: int,
    sender: FakeSender | None = None,
    db_path: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Approve a PENDING draft, populate parent outbox messages, and trigger sending.

    - Only allowed from status 'PENDING'.
    - Double approve is a safe no-op (does not re-queue or re-send).
    """
    active_sender = sender or default_sender

    with db_session(db_path) as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,)).fetchone()
        if not draft:
            raise KeyError(f"Draft {draft_id} not found")

        # Double approval is a safe no-op
        if draft["status"] == "APPROVED":
            return {"status": "already_approved", "draft_id": draft_id, "message": "Draft was already approved"}

        if draft["status"] != "PENDING":
            raise ValueError(f"Cannot approve draft with status '{draft['status']}'. Only PENDING drafts can be approved.")

        # Update draft status to APPROVED
        conn.execute(
            "UPDATE drafts SET status = 'APPROVED', updated_at = datetime('now') WHERE id = ?;",
            (draft_id,),
        )

        # Queue recipient parent notifications if applicable (generic, no other students' info)
        _populate_outbox_for_draft(conn, dict(draft), client=client)

    # Dispatch queued messages using the sender
    dispatch_result = dispatch_outbox_for_draft(draft_id, sender=active_sender, db_path=db_path)

    return {
        "status": "approved",
        "draft_id": draft_id,
        "dispatched": dispatch_result,
    }


def reject_draft(draft_id: int, db_path: str | None = None) -> dict[str, Any]:
    """Reject a PENDING draft. Status becomes REJECTED and zero messages are sent."""
    with db_session(db_path) as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,)).fetchone()
        if not draft:
            raise KeyError(f"Draft {draft_id} not found")

        if draft["status"] == "REJECTED":
            return {"status": "already_rejected", "draft_id": draft_id}

        if draft["status"] != "PENDING":
            raise ValueError(f"Cannot reject draft with status '{draft['status']}'. Only PENDING drafts can be rejected.")

        conn.execute(
            "UPDATE drafts SET status = 'REJECTED', updated_at = datetime('now') WHERE id = ?;",
            (draft_id,),
        )

    return {"status": "rejected", "draft_id": draft_id}


def _populate_outbox_for_draft(
    conn: Any,
    draft: dict[str, Any],
    client: httpx.Client | None = None,
) -> None:
    """Generate and queue bilingual messages for affected parents into the outbox."""
    draft_type = draft["type"]
    target_id = draft.get("target_id")

    # Principal summaries and ALL_CLEAR create no parent messages
    if draft_type in ("PRINCIPAL_SUMMARY", "ALL_CLEAR"):
        return

    messages_to_queue: list[tuple[str, str, str]] = []  # (recipient_id, msg_en, msg_hi)

    if draft_type == "ROUTE_DELAY" and target_id:
        route_res = get_route(target_id, client=client)
        route_name = route_res.get("data", {}).get("name", f"Route {target_id}")

        msg_en = (
            f"Dear Parent, Due to heavy rainfall and potential waterlogging along {route_name}, "
            "school bus pickup and drop-off may be delayed by approximately 20-30 minutes. "
            "Thank you for your patience and understanding."
        )
        msg_hi = (
            f"प्रिय अभिभावक, {route_name} पर भारी बारिश और संभावित जलभराव के कारण, "
            "स्कूल बस सेवा में लगभग 20-30 मिनट की देरी हो सकती है। "
            "आपके धैर्य और सहयोग के लिए धन्यवाद।"
        )

        # Get all students on this bus route
        stu_res = get_students(client=client)
        students = stu_res.get("data", [])
        for s in students:
            route_id = s.get("busRouteId") or s.get("bus_route_id")
            if route_id == target_id:
                messages_to_queue.append((s["id"], msg_en, msg_hi))

    elif draft_type == "EVENT_OUTDOOR" and target_id:
        events_res = get_events(client=client)
        events = events_res.get("data", [])
        matched_event = next((e for e in events if e.get("id") == target_id), None)
        title = matched_event.get("title", "School Event") if matched_event else "School Event"
        event_date = matched_event.get("date", draft["date"]) if matched_event else draft["date"]

        msg_en = (
            f"Dear Parent, Due to adverse weather conditions, outdoor activities for '{title}' "
            f"scheduled on {event_date} will be moved indoors or postponed. "
            "Regular academic timings remain unchanged."
        )
        msg_hi = (
            f"प्रिय अभिभावक, मौसम की प्रतिकूल परिस्थितियों के कारण, {event_date} को आयोजित ہونے वाले "
            f"'{title}' कार्यक्रम की बाहरी गतिविधियों को इनडोर स्थानांतरित या स्थगित कर दिया गया है। "
            "स्कूल का सामान्य समय अपरिवर्तित रहेगा।"
        )

        event_classes = matched_event.get("classes", []) if matched_event else []
        if isinstance(event_classes, str):
            event_classes = [event_classes]

        stu_res = get_students(client=client)
        students = stu_res.get("data", [])
        for s in students:
            s_class = s.get("class") or s.get("class_name")
            if s_class in event_classes:
                messages_to_queue.append((s["id"], msg_en, msg_hi))

    # Insert into outbox with UNIQUE(draft_id, recipient_id) constraint
    for recipient_id, msg_en, msg_hi in messages_to_queue:
        conn.execute(
            """
            INSERT OR IGNORE INTO outbox (draft_id, recipient_id, message_en, message_hi, status, attempts)
            VALUES (?, ?, ?, ?, 'QUEUED', 0);
            """,
            (draft["id"], recipient_id, msg_en, msg_hi),
        )


def dispatch_outbox_for_draft(
    draft_id: int | None = None,
    sender: FakeSender | None = None,
    max_attempts: int = MAX_SEND_ATTEMPTS,
    db_path: str | None = None,
) -> dict[str, int]:
    """Deliver queued and retriable failed outbox messages.

    - Messages already SENT are NEVER resent.
    - Failed messages are retried only up to max_attempts.
    """
    active_sender = sender or default_sender

    query = "SELECT * FROM outbox WHERE status IN ('QUEUED', 'FAILED') AND attempts < ?"
    params: list[Any] = [max_attempts]
    if draft_id is not None:
        query += " AND draft_id = ?"
        params.append(draft_id)

    delivered_count = 0
    failed_count = 0

    with db_session(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

        for row in rows:
            msg_id = row["id"]
            recipient_id = row["recipient_id"]
            msg_en = row["message_en"]
            msg_hi = row["message_hi"]
            attempts = row["attempts"] + 1

            success = active_sender.send(recipient_id, msg_en, msg_hi)
            new_status = "SENT" if success else "FAILED"

            if success:
                delivered_count += 1
            else:
                failed_count += 1

            conn.execute(
                """
                UPDATE outbox
                SET status = ?, attempts = ?, last_attempt_at = datetime('now')
                WHERE id = ?;
                """,
                (new_status, attempts, msg_id),
            )

    return {"delivered": delivered_count, "failed": failed_count}


def list_messages(
    draft_id: int | None = None,
    status: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """List outbox messages with optional filters."""
    query = "SELECT * FROM outbox WHERE 1=1"
    params: list[Any] = []
    if draft_id is not None:
        query += " AND draft_id = ?"
        params.append(draft_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id ASC;"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
