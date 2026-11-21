"""Controlled single- and multi-agent workflows for frontend regression tasks."""

from __future__ import annotations

import json
from typing import Any

from opencollab import workflow
from opencollab.tools import builtin_tools
from opencollab.workflows import WorkflowContext

TOTAL_BUDGET = 16_000
DEVELOPER_BUDGET = 10_000
QA_BUDGET = 3_000
REPAIR_BUDGET = 3_000

DEVELOPER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["summary", "tests_run", "known_risks"],
    "properties": {
        "summary": {"type": "string"},
        "tests_run": {"type": "array", "items": {"type": "string"}},
        "known_risks": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

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

REPAIR_SCHEMA = DEVELOPER_SCHEMA

DEVELOPER_PROMPT = """\
You are Frontend Developer. Implement the requested change in the repository you can access.

Task:
{goal}

Work as an engineer, not as a commentator: inspect the existing implementation, make the smallest
coherent source change, and verify it. You may run the public build and tests. Do not delete, weaken,
skip, or rewrite existing tests. Do not inspect paths outside this task workspace. Preserve existing
accessibility and adjacent UI states. In the final structured response, list exact commands actually
run and any remaining risks. Do not claim a check you did not run.
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

REPAIR_PROMPT = """\
You are Frontend Developer returning for one bounded repair round. The Regression QA agent found
evidence after your initial implementation. Reproduce the valid findings, repair them without weakening
tests, and rerun the smallest sufficient verification.

Task:
{goal}

QA report:
{qa_report}

Current diff:
{diff}

If a finding is not reproducible, preserve correct behavior and explain that in known_risks. Do not add
unrelated features. In the final structured response, list only commands actually run.
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
    report = await ctx.agent(
        DEVELOPER_PROMPT.format(goal=goal),
        schema=DEVELOPER_SCHEMA,
        label="frontend-developer",
        tools=_developer_tools(allow_shell),
        isolation="shared",
        budget=TOTAL_BUDGET,
        timeout=900,
    )
    if not isinstance(report, dict):
        return {
            "status": "incomplete",
            "condition": "single",
            "error": "developer returned no structured report",
            "developer": report,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }
    return {
        "status": "ok",
        "condition": "single",
        "developer": report,
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
    developer = await ctx.agent(
        DEVELOPER_PROMPT.format(goal=goal),
        schema=DEVELOPER_SCHEMA,
        label="frontend-developer",
        tools=_developer_tools(allow_shell),
        isolation="shared",
        budget=DEVELOPER_BUDGET,
        timeout=720,
    )
    if not isinstance(developer, dict):
        return {
            "status": "incomplete",
            "condition": "dev-qa",
            "error": "developer returned no structured report; QA was not started",
            "developer": developer,
            "qa": None,
            "repair": None,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }
    first_diff = await ctx.diff() or "(no diff available)"

    await ctx.phase("regression-review")
    qa = await ctx.agent(
        QA_PROMPT.format(
            goal=goal,
            developer_report=json.dumps(developer, ensure_ascii=False, indent=2),
            diff=first_diff,
        ),
        schema=QA_SCHEMA,
        label="regression-qa",
        tools=_qa_tools(allow_shell),
        isolation="shared",
        budget=QA_BUDGET,
        timeout=360,
    )
    if not isinstance(qa, dict):
        return {
            "status": "incomplete",
            "condition": "dev-qa",
            "error": "regression QA returned no structured report",
            "developer": developer,
            "qa": qa,
            "repair": None,
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }

    repair = None
    if isinstance(qa, dict) and qa.get("verdict") == "FAIL":
        await ctx.phase("repair")
        repair = await ctx.agent(
            REPAIR_PROMPT.format(
                goal=goal,
                qa_report=json.dumps(qa, ensure_ascii=False, indent=2),
                diff=await ctx.diff() or "(no diff available)",
            ),
            schema=REPAIR_SCHEMA,
            label="frontend-developer-repair",
            tools=_developer_tools(allow_shell),
            isolation="shared",
            budget=REPAIR_BUDGET,
            timeout=360,
        )
        if not isinstance(repair, dict):
            return {
                "status": "incomplete",
                "condition": "dev-qa",
                "error": "repair developer returned no structured report",
                "developer": developer,
                "qa": qa,
                "repair": repair,
                "tokens_spent": ctx.tokens_spent(),
                "diff": await ctx.diff(),
                "agent_failures": list(ctx.agent_failures),
            }

    return {
        "status": "ok",
        "condition": "dev-qa",
        "developer": developer,
        "qa": qa,
        "repair": repair,
        "tokens_spent": ctx.tokens_spent(),
        "diff": await ctx.diff(),
        "agent_failures": list(ctx.agent_failures),
    }


__all__ = ["frontend_single", "frontend_dev_qa"]
