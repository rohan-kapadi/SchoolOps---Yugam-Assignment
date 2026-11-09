"""Agent API service exposing /ask, morning job, draft approvals, and messages on port 8000."""

from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_api.agent.orchestrator import ask_agent
from agent_api.database.db import init_db
from agent_api.database.models import (
    DraftSchema,
    DraftUpdateSchema,
    JobRunSchema,
    OutboxMessageSchema,
)
from agent_api.services.morning_workflow import run_morning_workflow
from agent_api.services.notification_service import (
    approve_draft,
    get_draft,
    list_drafts,
    list_messages,
    reject_draft,
    update_draft,
)


# Ensure database tables exist upon module loading
init_db()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SchoolOps Agent API",
    summary="Principal-facing AI agent orchestrator with grounded tool calling and approval workflow.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural language question for the school assistant")


class AskResponse(BaseModel):
    answer: str
    tool_trace: list[dict[str, Any]]
    sources: list[str]


class RunJobRequest(BaseModel):
    date: str | None = Field(default=None, description="Optional target date in YYYY-MM-DD format")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agent_api"}


# ==========================================
# Agent /ask endpoint
# ==========================================

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Answer natural-language questions using grounded tool calling."""
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    try:
        result = ask_agent(req.question)
    except Exception as exc:
        err_msg = str(exc)
        if any(term in err_msg for term in ["503", "UNAVAILABLE", "high demand"]):
            raise HTTPException(
                status_code=503,
                detail="The AI model is temporarily experiencing high demand on Google's servers. Please try your question again in a moment.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Agent error: {err_msg}") from exc

    return AskResponse(
        answer=result.get("answer", ""),
        tool_trace=result.get("tool_trace", []),
        sources=result.get("sources", []),
    )


# ==========================================
# Morning Job Endpoints
# ==========================================

@app.post("/jobs/morning/run")
def trigger_morning_job(req: RunJobRequest | None = None) -> dict[str, Any]:
    """Manually trigger the 06:00 morning operational check for today (or specified date)."""
    target_date = req.date if req and req.date else None
    return run_morning_workflow(run_date=target_date)


# ==========================================
# Drafts Management & Approval Endpoints
# ==========================================

@app.get("/drafts", response_model=list[DraftSchema])
def get_all_drafts(
    status: str | None = Query(default=None, description="Filter by status (PENDING, APPROVED, REJECTED, ALL_CLEAR)"),
    date: str | None = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
) -> list[dict[str, Any]]:
    """List operational drafts created by the morning workflow."""
    return list_drafts(status=status, run_date=date)


@app.get("/drafts/{draft_id}", response_model=DraftSchema)
def get_single_draft(draft_id: int) -> dict[str, Any]:
    """Retrieve details of a single draft by ID."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    return draft


@app.patch("/drafts/{draft_id}", response_model=DraftSchema)
def modify_draft(draft_id: int, req: DraftUpdateSchema) -> dict[str, Any]:
    """Edit summary text or principal note on a PENDING draft."""
    try:
        updated = update_draft(
            draft_id=draft_id,
            summary=req.summary,
            principal_note=req.principal_note,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/drafts/{draft_id}/approve")
def approve_single_draft(draft_id: int) -> dict[str, Any]:
    """Principal approval: transitions draft to APPROVED and dispatches parent notifications."""
    try:
        return approve_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/drafts/{draft_id}/reject")
def reject_single_draft(draft_id: int) -> dict[str, Any]:
    """Principal rejection: transitions draft to REJECTED. No parent notifications are sent."""
    try:
        return reject_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


# ==========================================
# Outbox Messages Endpoints
# ==========================================

@app.get("/messages", response_model=list[OutboxMessageSchema])
def get_messages(
    draft_id: int | None = Query(default=None, description="Filter by draft ID"),
    status: str | None = Query(default=None, description="Filter by message status (QUEUED, SENT, FAILED)"),
) -> list[dict[str, Any]]:
    """List sent and queued parent messages in the outbox."""
    return list_messages(draft_id=draft_id, status=status)
