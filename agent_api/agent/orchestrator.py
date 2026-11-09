"""Tool-calling agent orchestrator with loop control, trace, and grounded answers."""

import os
import time
from typing import Any
from google import genai
from google.genai import types

from agent_api.agent.prompts import SYSTEM_PROMPT
from agent_api.agent.tool_registry import (
    GENAI_TOOL_DEFINITION,
    TOOL_DISPATCH,
)
from agent_api.config import LLM_API_KEY, LLM_MODEL

MAX_TOOL_CALLS = 8
DEFAULT_MODEL = LLM_MODEL


class AgentOrchestrator:
    """Orchestrates multi-turn function calling with hard limits and full tracing."""

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
        max_tool_calls: int = MAX_TOOL_CALLS,
    ) -> None:
        self.api_key = api_key or LLM_API_KEY or os.getenv("LLM_API_KEY", "")
        self.model = model
        self.max_tool_calls = max_tool_calls

        if client is not None:
            self.client = client
        elif self.api_key:
            self.client = genai.Client(
                api_key=self.api_key,
                http_options={"api_version": "v1beta"},
            )
        else:
            self.client = None

    def ask(self, question: str) -> dict[str, Any]:
        """Execute the question-answering workflow via tool-calling loop."""
        if not self.client:
            return {
                "answer": "LLM client is not configured. Please set LLM_API_KEY in .env.",
                "tool_trace": [],
                "sources": [],
            }

        tool_trace: list[dict[str, Any]] = []
        sources: list[str] = []
        tool_call_count = 0

        # Construct configuration with tools and system instruction
        config = types.GenerateContentConfig(
            tools=[GENAI_TOOL_DEFINITION],
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        )

        contents: list[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)],
            )
        ]

        final_answer = ""

        while tool_call_count < self.max_tool_calls:
            response = self._call_model_with_retry(contents, config)
            function_calls = getattr(response, "function_calls", None)

            # If no function calls, the model provided its final natural language answer
            if not function_calls:
                final_answer = response.text or ""
                break

            # Append the model's function-calling turn to history
            if getattr(response, "candidates", None) and response.candidates:
                contents.append(response.candidates[0].content)

            # Process each requested function call
            for call in function_calls:
                if tool_call_count >= self.max_tool_calls:
                    break

                tool_name = call.name
                tool_args = call.args or {}
                tool_call_count += 1

                handler = TOOL_DISPATCH.get(tool_name)
                if handler is None:
                    tool_result = {"status": "error", "reason": f"Unknown tool '{tool_name}'"}
                    status = "error"
                else:
                    try:
                        tool_result = handler(**tool_args)
                        status = tool_result.get("status", "ok")
                        if "source" in tool_result:
                            sources.append(tool_result["source"])
                    except Exception as exc:
                        tool_result = {"status": "error", "reason": str(exc)}
                        status = "error"

                tool_trace.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "status": status,
                })

                # Append function result back to context
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=tool_name,
                                response=tool_result,
                            )
                        ],
                    )
                )

        # If max tool calls limit was reached without final response, request synthesis
        if not final_answer:
            final_config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Maximum tool call limit reached. Please provide the best final answer based on the data retrieved so far."
                        )
                    ],
                )
            )
            final_res = self._call_model_with_retry(contents, final_config)
            final_answer = getattr(final_res, "text", "") or "Could not synthesize answer within tool limit."

        # Deduplicate sources preserving order
        unique_sources = list(dict.fromkeys(sources))

        return {
            "answer": final_answer,
            "tool_trace": tool_trace,
            "sources": unique_sources,
        }

    def _call_model_with_retry(self, contents: list[Any], config: Any, retries: int = 3) -> Any:
        """Call LLM with exponential backoff for transient server errors (503/500/502) and rate limits (429).
        Falls back to a lighter model if the primary model is unavailable due to high demand.
        """
        models = [self.model]
        if "flash-lite" not in self.model:
            models.append("gemini-3.1-flash-lite")

        last_error = None
        for model_name in models:
            for attempt in range(retries):
                try:
                    return self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                except Exception as exc:
                    last_error = exc
                    err_str = str(exc)
                    is_transient = any(
                        term in err_str
                        for term in [
                            "429",
                            "RESOURCE_EXHAUSTED",
                            "503",
                            "UNAVAILABLE",
                            "500",
                            "502",
                            "504",
                            "high demand",
                        ]
                    )
                    if is_transient and attempt < retries - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    if is_transient:
                        # Try next model in fallback chain
                        break
                    raise

        raise last_error


# Singleton default orchestrator instance
default_orchestrator = AgentOrchestrator()


def ask_agent(question: str) -> dict[str, Any]:
    """Convenience helper to query the default agent orchestrator."""
    return default_orchestrator.ask(question)
