"""A narrow model-visible verifier for the fixed frontend benchmark."""

from __future__ import annotations

from typing import Any


class FrontendVerifyTool:
    name = "verify_frontend"
    description = (
        "Run the fixed frontend verification command: "
        "`npm run build && npm run test:public`. Use once after editing."
    )
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}
    default_timeout = 300.0
    disable_outer_timeout = False

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute_with_runtime(self, _params: dict[str, Any], runtime: Any) -> str:
        environment = runtime.environment
        if environment is None:
            return "Error: no execution environment available."
        result = await environment.exec_cmd(
            "npm run build && npm run test:public",
            timeout=self.default_timeout,
        )
        observations = getattr(runtime, "observations", None)
        if observations is not None:
            observations.record_execution(
                exit_code=result.returncode,
                timed_out=getattr(result, "timed_out", None),
            )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        if len(output) > 4_000:
            output = output[-4_000:]
        return f"Exit code: {result.returncode}\n{output}".rstrip()
