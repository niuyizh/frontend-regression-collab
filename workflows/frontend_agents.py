"""Controlled single- and multi-agent workflows for frontend regression tasks."""

from __future__ import annotations

import re
from typing import Any

from opencollab import workflow
from opencollab.tools import builtin_tools
from opencollab.workflows import WorkflowContext

from .frontend_verify import FrontendVerifyTool

TOTAL_BUDGET = 48_000
DEVELOPER_BUDGET = 30_000
QA_BUDGET = 6_000
REPAIR_BUDGET = 18_000

DEVELOPER_SYSTEM_PROMPT = """\
You are Frontend Developer. Work as an engineer, not as a commentator: inspect the existing
implementation, make the smallest
coherent source change, and verify it. You may run the public build and tests. Do not delete, weaken,
skip, or rewrite existing tests. Do not inspect paths outside this task workspace. Preserve existing
accessibility and adjacent UI states. In the final response, concisely list the change, exact commands
actually run, and any remaining risks. Do not claim a check you did not run.

TASK.md names the primary source files; read those directly instead of listing or dumping the whole
repository. When TASK.md supplies a relevant line window, use file_read offset/limit exactly instead
of reading the whole file. Land the first targeted edit no later than your third response. Prefer file_write
mode=str_replace with an exact, unique old_str for existing files. After editing, call verify_frontend
once; it runs the verification command fixed by the task workspace.
"""

QA_SYSTEM_PROMPT = """\
You are Regression QA performing a bounded independent diff review. The developer already implemented
the new requirement and ran the public checks. Do not repeat those checks. Focus on old behavior the
diff may affect and UI states that the developer report did not cover: keyboard/focus, cancellation,
persistence, responsive boundaries, and loading/error/empty transitions as relevant.

Your first line must be exactly `VERDICT: PASS` or `VERDICT: FAIL`. Choose FAIL only for a concrete,
repairable regression or unmet acceptance criterion supported by the supplied diff. For each FAIL
finding name severity, affected behavior, exact diff evidence, reproduction, and a bounded fix. Choose
PASS when no such finding is supported; do not invent findings to justify your role.
"""

QA_PROMPT = """\
Review this handoff without tools.

Task:
{goal}

Developer report:
{developer_report}

Current diff:
{diff}

"""

REPAIR_SYSTEM_PROMPT = """\
You are Frontend Developer returning for one bounded repair round. Reproduce valid Regression QA
findings, repair them without weakening tests, and rerun the smallest sufficient verification. Do not
add unrelated features. In the final response, list only commands actually run.
"""

REPAIR_PROMPT = """\
The Regression QA agent found evidence after your initial implementation.

Task:
{goal}

QA report:
{qa_report}

Current diff:
{diff}

If a finding is not reproducible, preserve correct behavior and explain why.
"""


def _goal(args: dict[str, Any]) -> str:
    return str(args.get("goal") or args.get("task") or args.get("description") or "").strip()


def _allow_shell(args: dict[str, Any]) -> bool:
    value = args.get("allow_unisolated_shell", False)
    if not isinstance(value, bool):
        raise ValueError("allow_unisolated_shell must be a boolean")
    return value


def _developer_tools(allow_shell: bool) -> tuple[Any, ...]:
    tools = builtin_tools(
        "file_read", "file_write", "git_diff", headless=not allow_shell,
    )
    return (*tools, FrontendVerifyTool())


def _agent_run_record(run: Any) -> dict[str, Any]:
    return {
        "status": str(run.status),
        "reason": str(run.reason) if run.reason else None,
        "tokens": int(run.tokens),
        "steps": int(run.steps),
        "cleanup_complete": bool(run.cleanup_complete),
        "workspace_ready": bool(run.workspace_ready),
    }


def _agent_run_ok(run: Any) -> bool:
    return (
        run.status == "completed"
        and isinstance(run.output, str)
        and bool(run.output.strip())
        and bool(run.cleanup_complete)
        and bool(run.workspace_ready)
    )


def _qa_verdict(output: Any) -> str | None:
    if not isinstance(output, str):
        return None
    first_line = output.splitlines()[0].strip() if output.splitlines() else ""
    match = re.fullmatch(r"VERDICT:\s*(PASS|FAIL)", first_line, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


@workflow(
    name="frontend-single",
    description="One frontend developer with the full fixed budget",
    phases=["implement"],
)
async def frontend_single(ctx: WorkflowContext, args: dict[str, Any]) -> dict[str, Any]:
    goal = _goal(args)
    if not goal:
        return {"status": "error", "error": 'missing "goal"'}
    allow_shell = _allow_shell(args)
    await ctx.phase("implement")
    developer_run = await ctx.agent_run(
        goal,
        label="frontend-developer",
        tools=_developer_tools(allow_shell),
        isolation="shared",
        budget=TOTAL_BUDGET,
        timeout=900,
        max_steps=8,
        system_prompt=DEVELOPER_SYSTEM_PROMPT,
    )
    report = developer_run.output
    if not _agent_run_ok(developer_run):
        return {
            "status": "incomplete",
            "condition": "single",
            "error": developer_run.reason or "developer did not complete with a report",
            "developer": report,
            "developer_outcome": _agent_run_record(developer_run),
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }
    return {
        "status": "ok",
        "condition": "single",
        "developer": report,
        "developer_outcome": _agent_run_record(developer_run),
        "tokens_spent": ctx.tokens_spent(),
        "diff": await ctx.diff(),
        "agent_failures": list(ctx.agent_failures),
    }


@workflow(
    name="frontend-dev-qa",
    description="Frontend developer, regression-focused QA, and one evidence-driven repair round",
    phases=["implement", "regression-review", "repair"],
)
async def frontend_dev_qa(ctx: WorkflowContext, args: dict[str, Any]) -> dict[str, Any]:
    goal = _goal(args)
    if not goal:
        return {"status": "error", "error": 'missing "goal"'}
    allow_shell = _allow_shell(args)

    await ctx.phase("implement")
    developer_run = await ctx.agent_run(
        goal,
        label="frontend-developer",
        tools=_developer_tools(allow_shell),
        isolation="shared",
        budget=DEVELOPER_BUDGET,
        timeout=720,
        max_steps=8,
        system_prompt=DEVELOPER_SYSTEM_PROMPT,
    )
    developer = developer_run.output
    if not _agent_run_ok(developer_run):
        return {
            "status": "incomplete",
            "condition": "dev-qa",
            "error": developer_run.reason or "developer did not complete; QA was not started",
            "developer": developer,
            "developer_outcome": _agent_run_record(developer_run),
            "qa": None,
            "repair": None,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }
    first_diff = await ctx.diff() or "(no diff available)"

    await ctx.phase("regression-review")
    qa_run = await ctx.agent_run(
        QA_PROMPT.format(
            goal=goal,
            developer_report=developer,
            diff=first_diff,
        ),
        label="regression-qa",
        tools=(),
        isolation="shared",
        budget=QA_BUDGET,
        timeout=360,
        max_steps=1,
        system_prompt=QA_SYSTEM_PROMPT,
    )
    verdict = _qa_verdict(qa_run.output)
    qa = {"verdict": verdict, "report": qa_run.output} if verdict else None
    if not _agent_run_ok(qa_run) or qa is None:
        return {
            "status": "incomplete",
            "condition": "dev-qa",
            "error": qa_run.reason or "regression QA returned no parseable verdict",
            "developer": developer,
            "developer_outcome": _agent_run_record(developer_run),
            "qa": qa,
            "qa_outcome": _agent_run_record(qa_run),
            "repair": None,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }

    repair = None
    if qa["verdict"] == "FAIL":
        await ctx.phase("repair")
        repair_run = await ctx.agent_run(
            REPAIR_PROMPT.format(
                goal=goal,
                qa_report=qa["report"],
                diff=await ctx.diff() or "(no diff available)",
            ),
            label="frontend-developer-repair",
            tools=_developer_tools(allow_shell),
            isolation="shared",
            budget=REPAIR_BUDGET,
            timeout=360,
            max_steps=8,
            system_prompt=REPAIR_SYSTEM_PROMPT,
        )
        repair = repair_run.output
        if not _agent_run_ok(repair_run):
            return {
                "status": "incomplete",
                "condition": "dev-qa",
                "error": repair_run.reason or "repair developer did not complete with a report",
                "developer": developer,
                "developer_outcome": _agent_run_record(developer_run),
                "qa": qa,
                "qa_outcome": _agent_run_record(qa_run),
                "repair": repair,
                "repair_outcome": _agent_run_record(repair_run),
                "tokens_spent": ctx.tokens_spent(),
                "diff": await ctx.diff(),
                "agent_failures": list(ctx.agent_failures),
            }

    return {
        "status": "ok",
        "condition": "dev-qa",
        "developer": developer,
        "developer_outcome": _agent_run_record(developer_run),
        "qa": qa,
        "qa_outcome": _agent_run_record(qa_run),
        "repair": repair,
        "repair_outcome": _agent_run_record(repair_run) if repair is not None else None,
        "tokens_spent": ctx.tokens_spent(),
        "diff": await ctx.diff(),
        "agent_failures": list(ctx.agent_failures),
    }


__all__ = ["frontend_single", "frontend_dev_qa"]
