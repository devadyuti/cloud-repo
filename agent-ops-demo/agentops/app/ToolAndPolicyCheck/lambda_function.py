"""
R4 deterministic grader (code-based evaluator).

Checks — with zero LLM involvement, so the result is fully reproducible —
that the recorded session called the EXPECTED tool. For a weather question the
agent must invoke the `weather` tool; if it answered without the tool, that is a
deterministic FAIL.

This is the "expected tool called" half of the R4 deterministic grader. It reads
the OpenTelemetry spans AgentCore hands the evaluator (scope
strands.telemetry.tracer): tool calls appear as spans with
gen_ai.operation.name == "execute_tool" and a gen_ai.tool.name attribute, and
also as gen_ai.assistant.message events carrying a toolUse block.
"""

import json

from bedrock_agentcore.evaluation.custom_code_based_evaluators import (
    custom_code_based_evaluator,
    EvaluatorInput,
    EvaluatorOutput,
)

EXPECTED_TOOL = "weather"


def _iter_spans(session_spans):
    """Yield span dicts regardless of the exact container shape."""
    if session_spans is None:
        return
    if isinstance(session_spans, dict):
        session_spans = session_spans.get("spans", session_spans.values())
    for s in session_spans or []:
        if isinstance(s, dict):
            yield s


def _tools_called(session_spans):
    """Collect every tool name invoked across the session's spans."""
    tools = set()
    for span in _iter_spans(session_spans):
        attrs = span.get("attributes", {}) or {}
        # Direct tool-execution span.
        if attrs.get("gen_ai.operation.name") == "execute_tool":
            name = attrs.get("gen_ai.tool.name")
            if name:
                tools.add(name)
        # Tool name embedded in the span name, e.g. "execute_tool weather".
        name = span.get("name", "")
        if isinstance(name, str) and name.startswith("execute_tool "):
            tools.add(name.split(" ", 1)[1].strip())
        # toolUse inside assistant-message events.
        for ev in span.get("events", []) or []:
            if ev.get("name") == "gen_ai.assistant.message":
                content = (ev.get("attributes", {}) or {}).get("content", "")
                if isinstance(content, str) and '"name"' in content:
                    try:
                        for block in json.loads(content):
                            tu = block.get("toolUse") if isinstance(block, dict) else None
                            if tu and tu.get("name"):
                                tools.add(tu["name"])
                    except Exception:
                        if EXPECTED_TOOL in content:
                            tools.add(EXPECTED_TOOL)
    return tools


@custom_code_based_evaluator()
def handler(input: EvaluatorInput, context) -> EvaluatorOutput:
    tools = _tools_called(getattr(input, "session_spans", None))
    called = EXPECTED_TOOL in tools

    if called:
        return EvaluatorOutput(
            value=1.0,
            label="Pass",
            explanation=(
                f"Expected tool '{EXPECTED_TOOL}' was called. "
                f"Tools observed: {sorted(tools) or 'none'}."
            ),
        )
    return EvaluatorOutput(
        value=0.0,
        label="Fail",
        explanation=(
            f"Expected tool '{EXPECTED_TOOL}' was NOT called. "
            f"Tools observed: {sorted(tools) or 'none'}."
        ),
    )
