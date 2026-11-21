"""Preserve terminal status for schema-bound OpenCollab workflow agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


AgentStatus = Literal["completed", "stopped", "failed", "incomplete"]


@dataclass(frozen=True, slots=True)
class StructuredAgentOutcome:
    output: dict[str, Any] | None
    status: AgentStatus
    reason: str | None
    sessions_started: int

    @property
    def ok(self) -> bool:
        return self.status == "completed" and isinstance(self.output, dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _phase_value(session: Any) -> str | None:
    state = getattr(session, "state", None)
    phase = getattr(state, "phase", None)
    value = getattr(phase, "value", phase)
    return str(value) if value is not None else None


def _terminal_reason(session: Any) -> str | None:
    reason = getattr(getattr(session, "state", None), "terminal_reason", None)
    return str(reason) if reason else None


def _classify(
    output: Any,
    sessions: tuple[Any, ...],
) -> tuple[AgentStatus, str | None]:
    if isinstance(output, dict):
        return "completed", None

    for session in reversed(sessions):
        phase = _phase_value(session)
        if phase == "error":
            return "failed", _terminal_reason(session)
        if phase == "stopped":
            return "stopped", _terminal_reason(session)
    return "incomplete", "agent returned no schema-valid output"


async def run_structured_agent_checked(
    ctx: Any,
    prompt: str,
    *,
    schema: dict[str, Any],
    **kwargs: Any,
) -> StructuredAgentOutcome:
    """Call ``ctx.agent(schema=...)`` and retain new sessions' terminal status."""
    before = len(ctx.sessions)
    output = await ctx.agent(prompt, schema=schema, **kwargs)
    new_sessions = tuple(ctx.sessions[before:])
    status, reason = _classify(output, new_sessions)
    return StructuredAgentOutcome(
        output=output if isinstance(output, dict) else None,
        status=status,
        reason=reason,
        sessions_started=len(new_sessions),
    )
