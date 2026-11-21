"""Offline reproduction for a stopped structured workflow agent losing its status."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from opencollab.application.workflow import WorkflowContext
from opencollab.domain.session import SessionPhase


SCHEMA = {
    "type": "object",
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}
STOP_REASON = (
    "budget exhausted before model call: conservative input reservation "
    "requires 7827 of 5750 remaining tokens, leaving no output headroom"
)


class BudgetStoppedSession:
    def __init__(self) -> None:
        self.state = SimpleNamespace(
            aid=0,
            messages=[],
            phase=SessionPhase.IDLE,
            terminal_reason=None,
        )
        self.used_tokens = 0
        self.step_count = 0

    async def add_user_message(self, content: str) -> None:
        self.state.messages.append({"role": "user", "content": content})

    async def run_loop(self, _cancel_event: asyncio.Event | None = None) -> None:
        self.state.phase = SessionPhase.STOPPED
        self.state.terminal_reason = STOP_REASON
        return None


class BudgetStoppedFactory:
    default_isolation = "shared"

    def build_workflow_session(self, **_kwargs: Any) -> BudgetStoppedSession:
        return BudgetStoppedSession()


async def main() -> None:
    ctx = WorkflowContext(BudgetStoppedFactory(), budget_total=16_000)
    payload = await ctx.agent(
        "Return a structured summary.",
        schema=SCHEMA,
        label="developer",
        budget=16_000,
    )
    observed = {
        "ctx.agent return": payload,
        "ctx.agent_failures": list(ctx.agent_failures),
        "child_sessions": [
            {
                "phase": session.state.phase.value,
                "terminal_reason": session.state.terminal_reason,
            }
            for session in ctx.sessions
        ],
    }
    print(json.dumps(observed, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
