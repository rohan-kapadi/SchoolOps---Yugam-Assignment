"""Unit tests for agent orchestrator, tool-calling loop, and /ask endpoint.

Uses mocked LLM and tools (no real external network calls).
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from agent_api.agent.orchestrator import AgentOrchestrator
from agent_api.main import app
from tests.conftest import MockFunctionCall, MockGenAIClient, MockModelResponse


def test_tool_loop_stops_at_max_calls():
    """Gate requirement: Tool loop terminates when reaching hard max (8 calls)."""
    # Create scripted responses that keep requesting tool calls forever
    infinite_tool_calls = [
        MockModelResponse(
            function_calls=[MockFunctionCall(name="get_events", args={})],
        )
        for _ in range(15)
    ]
    infinite_tool_calls.append(MockModelResponse(text="Final answer after limit"))

    mock_client = MockGenAIClient(infinite_tool_calls)
    orchestrator = AgentOrchestrator(client=mock_client, max_tool_calls=8)

    with patch("agent_api.agent.tool_registry.run_get_events") as mock_events:
        mock_events.return_value = {"status": "ok", "data": []}
        result = orchestrator.ask("Check all events repeatedly")

    # Loop must stop strictly at 8 tool calls
    assert len(result["tool_trace"]) == 8
    assert all(t["tool"] == "get_events" for t in result["tool_trace"])
    assert "answer" in result
    assert len(result["answer"]) > 0


def test_trace_and_sources_returned():
    """Gate requirement: Tool trace and sources are recorded and returned."""
    responses = [
        MockModelResponse(
            function_calls=[MockFunctionCall(name="get_events", args={})],
        ),
        MockModelResponse(
            text="Nilgiri Valley School has 5 upcoming events scheduled.",
            function_calls=None,
        ),
    ]

    mock_client = MockGenAIClient(responses)
    orchestrator = AgentOrchestrator(client=mock_client)

    with patch("agent_api.agent.tool_registry.run_get_events") as mock_events:
        mock_events.return_value = {
            "status": "ok",
            "data": [{"id": "E1", "title": "Sports Day"}],
        }
        result = orchestrator.ask("What events are happening?")

    assert len(result["tool_trace"]) == 1
    trace_entry = result["tool_trace"][0]
    assert trace_entry["tool"] == "get_events"
    assert trace_entry["status"] == "ok"
    assert "School API: /school/events" in result["sources"]
    assert "5 upcoming events" in result["answer"]


def test_ambiguous_riya_sharma_yields_clarification():
    """Gate requirement: Ambiguous student name returns clarification with class and stop."""
    responses = [
        MockModelResponse(
            function_calls=[MockFunctionCall(name="find_student", args={"name": "Riya Sharma"})],
        ),
        MockModelResponse(
            text=(
                "There are two students named Riya Sharma in the school records:\n"
                "- Riya Sharma in Class 6A (Bus Stop: Vaishali Nagar)\n"
                "- Riya Sharma in Class 7A (Bus Stop: Malviya Nagar)\n"
                "Please clarify which student you are referring to."
            ),
            function_calls=None,
        ),
    ]

    mock_client = MockGenAIClient(responses)
    orchestrator = AgentOrchestrator(client=mock_client)

    with patch("agent_api.agent.tool_registry.run_get_students") as mock_students:
        mock_students.return_value = {
            "status": "ok",
            "data": [
                {"id": "S004", "name": "Riya Sharma", "class": "6A", "busStop": "Vaishali Nagar"},
                {"id": "S061", "name": "Riya Sharma", "class": "7A", "busStop": "Malviya Nagar"},
            ],
        }
        result = orchestrator.ask("What is Riya Sharma's bus stop?")

    # Verify tool execution and ambiguity handling
    assert len(result["tool_trace"]) == 1
    assert result["tool_trace"][0]["tool"] == "find_student"
    assert result["tool_trace"][0]["status"] == "ok"

    answer = result["answer"].lower()
    assert "6a" in answer and "7a" in answer
    assert "clarify" in answer or "which" in answer


def test_weather_failure_yields_could_not_be_checked():
    """Gate requirement: Weather failure / data_unavailable reports 'could not be checked'."""
    responses = [
        MockModelResponse(
            function_calls=[
                MockFunctionCall(
                    name="get_forecast",
                    args={"lat": 26.9124, "lon": 75.7873, "date": "2026-11-10"},
                )
            ],
        ),
        MockModelResponse(
            text="The weather forecast for tomorrow could not be checked due to an external service timeout.",
            function_calls=None,
        ),
    ]

    mock_client = MockGenAIClient(responses)
    orchestrator = AgentOrchestrator(client=mock_client)

    with patch("agent_api.agent.tool_registry.run_get_forecast") as mock_forecast:
        mock_forecast.return_value = {
            "status": "data_unavailable",
            "reason": "Open-Meteo connection timed out",
        }
        result = orchestrator.ask("What is tomorrow's weather?")

    assert len(result["tool_trace"]) == 1
    assert result["tool_trace"][0]["tool"] == "get_forecast"
    assert result["tool_trace"][0]["status"] == "data_unavailable"
    assert "could not be checked" in result["answer"].lower()


def test_ask_endpoint_fastapi():
    """Test FastAPI /ask endpoint behavior."""
    test_client = TestClient(app)

    # Empty question -> 422
    resp_empty = test_client.post("/ask", json={"question": "   "})
    assert resp_empty.status_code == 422

    # Successful call with mocked orchestrator
    with patch("agent_api.main.ask_agent") as mock_ask:
        mock_ask.return_value = {
            "answer": "Mocked principal response",
            "tool_trace": [{"tool": "get_events", "args": {}, "status": "ok"}],
            "sources": ["School API: /school/events"],
        }
        resp = test_client.post("/ask", json={"question": "Are there any events today?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Mocked principal response"
        assert len(data["tool_trace"]) == 1
        assert "School API: /school/events" in data["sources"]

