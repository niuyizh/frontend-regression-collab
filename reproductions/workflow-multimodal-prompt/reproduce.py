"""Offline reproduction: workflow agent_run rejects provider-supported image blocks."""

from __future__ import annotations

import asyncio
import json

from opencollab.adapters.llm.responses_provider import _messages_to_input
from opencollab.application.workflow_agent_run import WorkflowAgentRunMixin


CONTENT = [
    {"type": "text", "text": "Inspect the screenshot."},
    {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,AA==", "detail": "low"},
    },
]


async def main() -> None:
    _instructions, provider_input = _messages_to_input(
        [{"role": "user", "content": CONTENT}]
    )
    try:
        # Validation happens before the mixin accesses context state, so an
        # inert receiver is sufficient for this provider-independent repro.
        await WorkflowAgentRunMixin.agent_run(object(), CONTENT)  # type: ignore[arg-type]
    except ValueError as error:
        result = {
            "responses_adapter_accepts_image": provider_input[0]["content"][1]["type"]
            == "input_image",
            "workflow_agent_run_accepts_image": False,
            "actual_error": str(error),
        }
    else:
        result = {
            "responses_adapter_accepts_image": True,
            "workflow_agent_run_accepts_image": True,
            "actual_error": None,
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
