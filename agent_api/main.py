"""Agent API service exposing /ask and orchestrator endpoints on port 8000."""

from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_api.agent.orchestrator import ask_agent

app = FastAPI(
    title="SchoolOps Agent API",
    summary="Principal-facing AI agent orchestrator with grounded tool calling.",
    version="1.0.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural language question for the school assistant")


class AskResponse(BaseModel):
    answer: str
    tool_trace: list[dict[str, Any]]
    sources: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agent_api"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Answer natural-language questions using grounded tool calling."""
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    result = ask_agent(req.question)
    return AskResponse(
        answer=result.get("answer", ""),
        tool_trace=result.get("tool_trace", []),
        sources=result.get("sources", []),
    )
