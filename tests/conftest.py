"""Pytest fixtures and mock objects for agent testing."""

from dataclasses import dataclass, field
from typing import Any
import pytest


@dataclass
class MockFunctionCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class MockCandidateContent:
    role: str = "model"
    parts: list[Any] = field(default_factory=list)


@dataclass
class MockCandidate:
    content: MockCandidateContent = field(default_factory=MockCandidateContent)


@dataclass
class MockModelResponse:
    text: str | None = None
    function_calls: list[MockFunctionCall] | None = None
    candidates: list[MockCandidate] = field(default_factory=lambda: [MockCandidate()])


class MockGenAIClient:
    """Mock Google GenAI Client with scripted turn-by-turn responses."""

    def __init__(self, responses: list[MockModelResponse] | None = None) -> None:
        self.responses = responses or []
        self.call_history: list[dict[str, Any]] = []
        self._index = 0
        self.models = self

    def generate_content(self, model: str, contents: list[Any], config: Any = None) -> MockModelResponse:
        self.call_history.append({"model": model, "contents": contents, "config": config})
        if self._index < len(self.responses):
            res = self.responses[self._index]
            self._index += 1
            return res
        # Default fallback
        return MockModelResponse(text="Default mock answer", function_calls=None)


@pytest.fixture(autouse=True)
def fallback_school_api_in_tests(monkeypatch):
    """Ensure tests pass standalone even if the background School API server (:8001) is offline."""
    from fastapi.testclient import TestClient
    from agent_api.tools import school_tools
    from school_api.main import app as school_app

    orig_school_request = school_tools._school_request

    def smart_school_request(path: str, params: dict | None = None, timeout: float = 10.0, client: Any = None):
        res = orig_school_request(path, params=params, timeout=timeout, client=client)
        if res.get("status") == "data_unavailable" and "connection error" in str(res.get("reason", "")).lower():
            tc = TestClient(school_app)
            clean_params = {k: v for k, v in (params or {}).items() if v is not None}
            resp = tc.get(path, params=clean_params)
            return school_tools._handle_response(resp)
        return res

    monkeypatch.setattr(school_tools, "_school_request", smart_school_request)

