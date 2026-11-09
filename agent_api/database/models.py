"""Database table DDLs and Pydantic schemas for drafts, outbox, and job runs."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'ALL_CLEAR')),
    summary TEXT NOT NULL,
    principal_note TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    target_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    recipient_id TEXT NOT NULL,
    message_en TEXT NOT NULL,
    message_hi TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('QUEUED', 'SENT', 'FAILED')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (draft_id) REFERENCES drafts(id),
    UNIQUE (draft_id, recipient_id)
);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
"""


class DraftSchema(BaseModel):
    id: int
    date: str
    type: str
    status: str
    summary: str
    principal_note: str | None = None
    idempotency_key: str
    target_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DraftUpdateSchema(BaseModel):
    summary: str | None = None
    principal_note: str | None = None


class OutboxMessageSchema(BaseModel):
    id: int
    draft_id: int
    recipient_id: str
    message_en: str
    message_hi: str
    status: str
    attempts: int
    last_attempt_at: str | None = None
    created_at: str | None = None


class JobRunSchema(BaseModel):
    id: int
    run_date: str
    status: str
    started_at: str
    completed_at: str | None = None

