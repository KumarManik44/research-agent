
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


class ClaudeClient:
    """
    Wraps the google-genai SDK and exposes the same run_tool_loop() interface
    that the rest of the app expects.
    """

    def __init__(self, api_key: str, *, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        logger.info("GeminiClient initialised with model=%s", model)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_function_declarations(self, tools: list[ToolDef]) -> list[types.FunctionDeclaration]:
        """Convert our ToolDef list into Gemini FunctionDeclaration objects."""
        declarations = []
        for t in tools:
            declarations.append(
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=t.input_schema,
                )
            )
        return declarations

    # ------------------------------------------------------------------
    # Main agentic loop
    # ------------------------------------------------------------------

    async def run_tool_loop(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDef],
        on_tool_use: Callable[[ToolUse], Awaitable[Any]],
        max_turns: int = 20,
    ) -> str:
        """
        Runs an agentic tool-use loop with Gemini:
          1. Send the user prompt (+ system prompt + tools).
          2. If Gemini calls a tool → execute it via on_tool_use(), feed result back.
          3. Repeat until Gemini returns a final text response.
        Returns the final text report as a string.
        """

        function_declarations = self._build_function_declarations(tools)
        gemini_tools = [types.Tool(function_declarations=function_declarations)]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=gemini_tools,
            temperature=0.3,
        )

        # Conversation history — starts with the user message
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_prompt)],
            )
        ]

        for turn in range(max_turns):
            logger.debug("Gemini turn %d — sending %d content blocks", turn, len(contents))

            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason

            logger.debug("finish_reason=%s", finish_reason)

            # Collect all parts from this response
            response_parts = candidate.content.parts

            # Check for function calls in this response
            function_calls = [p for p in response_parts if p.function_call is not None]

            if not function_calls:
                # No tool calls — extract and return the final text
                text_parts = [p.text for p in response_parts if p.text]
                final_text = "\n".join(text_parts).strip()
                if final_text:
                    logger.debug("Gemini returned final text (%d chars)", len(final_text))
                    return final_text

                # Fallback: shouldn't happen but handle gracefully
                logger.warning("Gemini returned no text and no function calls on turn %d", turn)
                return "Research completed but no report was generated."

            # ---- There are function calls to handle ----

            # Add the assistant's response to history
            contents.append(
                types.Content(
                    role="model",
                    parts=response_parts,
                )
            )

            # Execute each tool call and collect results
            tool_result_parts: list[types.Part] = []

            for part in function_calls:
                fc = part.function_call
                tool_use = ToolUse(
                    id=fc.id or fc.name,
                    name=fc.name,
                    input=dict(fc.args) if fc.args else {},
                )

                logger.debug("Tool call: %s(%s)", tool_use.name, json.dumps(tool_use.input))

                try:
                    result = await on_tool_use(tool_use)
                except Exception as exc:
                    logger.exception("Tool %s raised an exception", tool_use.name)
                    result = {"error": str(exc)}

                logger.debug("Tool result for %s: %s chars", tool_use.name, len(str(result)))

                tool_result_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=tool_use.id,
                            name=tool_use.name,
                            response={"result": result},
                        )
                    )
                )

            # Add all tool results as a user turn
            contents.append(
                types.Content(
                    role="user",
                    parts=tool_result_parts,
                )
            )

        logger.warning("Reached max_turns=%d without a final response", max_turns)
        return "Research agent reached the maximum number of turns without completing."