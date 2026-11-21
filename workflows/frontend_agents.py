"""Controlled single- and multi-agent workflows for frontend regression tasks."""

from __future__ import annotations

import json
from typing import Any

from opencollab import workflow
from opencollab.tools import builtin_tools
from opencollab.workflows import WorkflowContext

from .status_aware_agent import run_structured_agent_checked

TOTAL_BUDGET = 36_000
DEVELOPER_BUDGET = 24_000
QA_BUDGET = 8_000
REPAIR_BUDGET = 12_000

QA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["verdict", "findings", "checks_run", "coverage_note"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "behavior", "evidence", "reproduction", "suggested_fix"],
                "properties": {
                    "severity": {"type": "string", "enum": ["blocking", "major", "minor"]},
                    "behavior": {"type": "string"},
                    "evidence": {"type": "string"},
                    "reproduction": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "checks_run": {"type": "array", "items": {"type": "string"}},
        "coverage_note": {"type": "string"},
    },
    "additionalProperties": False,
}

DEVELOPER_SYSTEM_PROMPT = """\
You are Frontend Developer. Work as an engineer, not as a commentator: inspect the existing
implementation, make the smallest
coherent source change, and verify it. You may run the public build and tests. Do not delete, weaken,
skip, or rewrite existing tests. Do not inspect paths outside this task workspace. Preserve existing
accessibility and adjacent UI states. In the final response, concisely list the change, exact commands
actually run, and any remaining risks. Do not claim a check you did not run.
"""

QA_PROMPT = """\
You are Regression QA. The developer has already implemented and checked the new requirement.
Your job is not to repeat the developer's completed checks. Inspect the current diff and focus on old
behaviors that the change may have affected, untested UI states, keyboard/focus behavior, cancellation,
persistence, responsive boundaries, and loading/error/empty transitions as relevant.

Task:
{goal}

Developer report:
{developer_report}

Current diff:
{diff}

You have read-only source and shell tools. Do not edit files. Run only targeted checks that add evidence
beyond the developer's listed commands. A finding must name an affected behavior, concrete evidence,
reproduction steps, and a bounded fix. Return PASS when you found no reproducible regression or unmet
acceptance criterion after those targeted checks; do not invent findings to justify your role.
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
    return builtin_tools(
        "apply_patch", "bash", "file_read", "grep", "git_diff",
        headless=not allow_shell,
    )


def _qa_tools(allow_shell: bool) -> tuple[Any, ...]:
    return builtin_tools(
        "bash", "file_read", "grep", "git_diff",
        headless=not allow_shell,
        allow_file_creation=False,
    )


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
        max_steps=12,
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
        max_steps=12,
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
    qa_run = await run_structured_agent_checked(
        ctx,
        QA_PROMPT.format(
            goal=goal,
            developer_report=developer,
            diff=first_diff,
        ),
        schema=QA_SCHEMA,
        label="regression-qa",
        tools=_qa_tools(allow_shell),
        isolation="shared",
        budget=QA_BUDGET,
        timeout=360,
    )
    qa = qa_run.output
    if not qa_run.ok:
        return {
            "status": "incomplete",
            "condition": "dev-qa",
            "error": qa_run.reason or "regression QA returned no structured report",
            "developer": developer,
            "developer_outcome": _agent_run_record(developer_run),
            "qa": qa,
            "qa_outcome": qa_run.as_dict(),
            "repair": None,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }

    repair = None
    if isinstance(qa, dict) and qa.get("verdict") == "FAIL":
        await ctx.phase("repair")
        repair_run = await ctx.agent_run(
            REPAIR_PROMPT.format(
                goal=goal,
                qa_report=json.dumps(qa, ensure_ascii=False, indent=2),
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
                "error": repair_run.reason or "repair developer returned no structured report",
                "developer": developer,
                "developer_outcome": _agent_run_record(developer_run),
                "qa": qa,
                "qa_outcome": qa_run.as_dict(),
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
        "qa_outcome": qa_run.as_dict(),
        "repair": repair,
        "repair_outcome": _agent_run_record(repair_run) if repair is not None else None,
        "tokens_spent": ctx.tokens_spent(),
        "diff": await ctx.diff(),
        "agent_failures": list(ctx.agent_failures),
    }


__all__ = ["frontend_single", "frontend_dev_qa"]
