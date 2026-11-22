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

RESILIENT_QA_SYSTEM_PROMPT = QA_SYSTEM_PROMPT + """\

The handoff may be artifact-first because the Developer stopped after writing code but before a
final narrative response. In that case, treat the supplied diff as the authoritative artifact and
do not infer success from the partial report. Return PASS or FAIL by the same evidence standard.
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


def _artifact_handoff_ok(run: Any, diff: str, *, previous_diff: str | None = None) -> bool:
    if (
        str(run.status) != "stopped"
        or not bool(run.cleanup_complete)
        or not bool(run.workspace_ready)
        or not diff.strip()
    ):
        return False
    return previous_diff is None or diff != previous_diff


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
    artifact_first = bool(args.get("_artifact_first_handoff", False))
    condition_name = "dev-qa-resilient" if artifact_first else "dev-qa"

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
    first_diff = await ctx.diff() or ""
    developer_recovered = False
    if not _agent_run_ok(developer_run):
        developer_recovered = artifact_first and _artifact_handoff_ok(
            developer_run, first_diff
        )
        if not developer_recovered:
            return {
                "status": "incomplete",
                "condition": condition_name,
                "error": developer_run.reason or "developer did not complete; QA was not started",
                "developer": developer,
                "developer_outcome": _agent_run_record(developer_run),
                "qa": None,
                "repair": None,
                "handoff_recovery": {"developer": False, "repair": False},
                "tokens_spent": ctx.tokens_spent(),
                "diff": first_diff,
                "agent_failures": list(ctx.agent_failures),
            }
        developer = (
            "Artifact-first handoff: Developer stopped before its final report; "
            "review the complete diff and terminal outcome below.\n\n"
            f"Partial output:\n{developer or '(none)'}\n\n"
            f"Terminal reason: {developer_run.reason or '(none)'}"
        )
    first_diff = first_diff or "(no diff available)"

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
        system_prompt=RESILIENT_QA_SYSTEM_PROMPT if artifact_first else QA_SYSTEM_PROMPT,
    )
    verdict = _qa_verdict(qa_run.output)
    qa = {"verdict": verdict, "report": qa_run.output} if verdict else None
    if not _agent_run_ok(qa_run) or qa is None:
        return {
            "status": "incomplete",
            "condition": condition_name,
            "error": qa_run.reason or "regression QA returned no parseable verdict",
            "developer": developer,
            "developer_outcome": _agent_run_record(developer_run),
            "qa": qa,
            "qa_outcome": _agent_run_record(qa_run),
            "repair": None,
            "handoff_recovery": {"developer": developer_recovered, "repair": False},
            "tokens_spent": ctx.tokens_spent(),
            "diff": await ctx.diff(),
            "agent_failures": list(ctx.agent_failures),
        }

    repair = None
    repair_recovered = False
    repair_run = None
    if qa["verdict"] == "FAIL":
        await ctx.phase("repair")
        before_repair_diff = await ctx.diff() or ""
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
        after_repair_diff = await ctx.diff() or ""
        if not _agent_run_ok(repair_run):
            repair_recovered = artifact_first and _artifact_handoff_ok(
                repair_run,
                after_repair_diff,
                previous_diff=before_repair_diff,
            )
            if not repair_recovered:
                return {
                    "status": "incomplete",
                    "condition": condition_name,
                    "error": repair_run.reason or "repair developer did not complete with a report",
                    "developer": developer,
                    "developer_outcome": _agent_run_record(developer_run),
                    "qa": qa,
                    "qa_outcome": _agent_run_record(qa_run),
                    "repair": repair,
                    "repair_outcome": _agent_run_record(repair_run),
                    "handoff_recovery": {
                        "developer": developer_recovered,
                        "repair": False,
                    },
                    "tokens_spent": ctx.tokens_spent(),
                    "diff": after_repair_diff,
                    "agent_failures": list(ctx.agent_failures),
                }
            repair = (
                "Artifact-first repair handoff: repair stopped before its final report, "
                "but changed the diff; external evaluation remains authoritative.\n\n"
                f"Partial output:\n{repair or '(none)'}\n\n"
                f"Terminal reason: {repair_run.reason or '(none)'}"
            )

    return {
        "status": "ok",
        "condition": condition_name,
        "developer": developer,
        "developer_outcome": _agent_run_record(developer_run),
        "qa": qa,
        "qa_outcome": _agent_run_record(qa_run),
        "repair": repair,
        "repair_outcome": _agent_run_record(repair_run) if repair_run is not None else None,
        "handoff_recovery": {
            "developer": developer_recovered,
            "repair": repair_recovered,
        },
        "tokens_spent": ctx.tokens_spent(),
        "diff": await ctx.diff(),
        "agent_failures": list(ctx.agent_failures),
    }


@workflow(
    name="frontend-dev-qa-resilient",
    description="Artifact-first Developer/QA workflow that can recover a stopped coding handoff",
    phases=["implement", "regression-review", "repair"],
)
async def frontend_dev_qa_resilient(
    ctx: WorkflowContext,
    args: dict[str, Any],
) -> dict[str, Any]:
    return await frontend_dev_qa(ctx, {**args, "_artifact_first_handoff": True})


__all__ = ["frontend_single", "frontend_dev_qa", "frontend_dev_qa_resilient"]
