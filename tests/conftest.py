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
