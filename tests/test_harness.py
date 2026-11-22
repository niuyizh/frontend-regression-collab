from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT))

from common import task_record  # noqa: E402
from run_experiment import _extract_json  # noqa: E402
from run_matrix import _has_recorded_result, matrix  # noqa: E402
from run_resilient_matrix import matrix as resilient_matrix  # noqa: E402
from summarize_results import condition_summary, distribution  # noqa: E402


def _workflow_module():
    path = ROOT / "workflows" / "frontend_agents.py"
    spec = importlib.util.spec_from_file_location("workflows.frontend_agents_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_has_five_distinct_tasks_with_prompt_files():
    data = json.loads((ROOT / "tasks" / "manifest.json").read_text(encoding="utf-8"))
    assert len(data["tasks"]) == 5
    assert len({item["id"] for item in data["tasks"]}) == 5
    for item in data["tasks"]:
        assert (ROOT / "tasks" / item["prompt_file"]).is_file()
        assert item["hidden_tests"] == 2
        assert task_record(item["id"])["title"]


def test_preregistered_matrix_has_all_tasks_once_and_three_key_repetitions():
    runs = matrix()
    assert len(runs) == 18
    assert len(set(runs)) == len(runs)
    for task_id in ("t03-sync-retry", "t04-responsive-nav"):
        for condition in ("single", "dev-qa"):
            assert {rep for task, cond, rep in runs if task == task_id and cond == condition} == {1, 2, 3}


def test_matrix_resume_requires_agent_and_evaluation_records(monkeypatch, tmp_path):
    monkeypatch.setattr("run_matrix.result_dir", lambda *_args: tmp_path)
    (tmp_path / "agent.json").write_text("{}", encoding="utf-8")
    assert not _has_recorded_result("task", "single", 1)
    (tmp_path / "evaluation.json").write_text("{}", encoding="utf-8")
    assert _has_recorded_result("task", "single", 1)


def test_resilient_matrix_matches_single_baseline_repetitions():
    runs = resilient_matrix()
    assert len(runs) == 9
    assert len(set(runs)) == len(runs)
    for task_id in ("t01-search", "t02-modal-priority", "t05-form-due-date"):
        assert {rep for task, _condition, rep in runs if task == task_id} == {1}
    for task_id in ("t03-sync-retry", "t04-responsive-nav"):
        assert {rep for task, _condition, rep in runs if task == task_id} == {1, 2, 3}
    assert {condition for _task, condition, _rep in runs} == {"dev-qa-resilient"}


def test_result_summary_reports_variation_and_strict_vs_external_success():
    assert distribution([1, 2, 3]) == {
        "n": 3,
        "mean": 2,
        "sample_sd": 1.0,
        "median": 2,
        "min": 1,
        "max": 3,
    }
    subset = [
        {
            "task_complete": True,
            "external_checks_passed": True,
            "agent_run_valid": True,
            "tokens": 10,
            "agent_seconds": 1.0,
            "qa_verdict": "PASS",
            "developer_recovered": False,
            "repair_recovered": False,
        },
        {
            "task_complete": False,
            "external_checks_passed": True,
            "agent_run_valid": False,
            "tokens": 20,
            "agent_seconds": 3.0,
            "qa_verdict": None,
            "developer_recovered": True,
            "repair_recovered": False,
        },
    ]
    summary = condition_summary(subset)
    assert summary["task_completion_rate"] == 0.5
    assert summary["external_checks_passed_rate"] == 1.0
    assert summary["invalid_agent_runs"] == 1
    assert summary["developer_handoffs_recovered"] == 1


def test_cli_json_extraction_prefers_final_payload():
    text = 'log with {embedded: braces}\n{"status": "ok", "tokens_spent": 42}\n'
    assert _extract_json(text) == {"status": "ok", "tokens_spent": 42}


def test_qa_verdict_requires_explicit_first_line_marker():
    module = _workflow_module()
    assert module._qa_verdict("VERDICT: PASS\nNo supported regression.") == "PASS"
    assert module._qa_verdict("VERDICT: FAIL\nMajor: focus is lost.") == "FAIL"
    assert module._qa_verdict("Looks good") is None


def test_developer_uses_targeted_write_tool_instead_of_unified_patch():
    module = _workflow_module()
    names = {tool.name for tool in module._developer_tools(True)}
    assert names == {"file_read", "file_write", "git_diff", "verify_frontend"}
    assert "bash" not in names
    assert "apply_patch" not in names


def test_artifact_handoff_requires_stopped_ready_run_and_changed_diff():
    module = _workflow_module()
    run = SimpleNamespace(
        status="stopped",
        cleanup_complete=True,
        workspace_ready=True,
    )
    assert module._artifact_handoff_ok(run, "diff --git a/a b/a")
    assert not module._artifact_handoff_ok(run, "")
    assert not module._artifact_handoff_ok(
        run,
        "same diff",
        previous_diff="same diff",
    )
    run.status = "failed"
    assert not module._artifact_handoff_ok(run, "diff --git a/a b/a")


class FakeContext:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.phases = []
        self.agent_failures = ()
        self.sessions = []

    async def phase(self, name):
        self.phases.append(name)

    async def agent(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return next(self.replies)

    async def agent_run(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        output = next(self.replies)
        return SimpleNamespace(
            output=output,
            status="completed" if isinstance(output, str) else "stopped",
            reason=None if isinstance(output, str) else "budget exhausted before model call",
            tokens=100,
            steps=2,
            cleanup_complete=True,
            workspace_ready=True,
        )

    async def diff(self):
        return "diff --git a/src/App.tsx b/src/App.tsx"

    def tokens_spent(self):
        return 321


@pytest.mark.asyncio
async def test_dev_qa_skips_repair_on_pass(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    developer = "Implemented and ran npm test"
    qa = "VERDICT: PASS\nNo supported regression."
    context = FakeContext([developer, qa])

    result = await module.frontend_dev_qa(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["repair"] is None
    assert [call["label"] for call in context.calls] == ["frontend-developer", "regression-qa"]
    assert [call["budget"] for call in context.calls] == [30_000, 6_000]


@pytest.mark.asyncio
async def test_dev_qa_uses_one_bounded_repair_on_fail(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    developer = "Implemented and ran npm test"
    qa = "VERDICT: FAIL\nMajor: x; evidence y; reproduce z; fix w."
    repair = "Fixed and ran npm test"
    context = FakeContext([developer, qa, repair])

    result = await module.frontend_dev_qa(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["repair"] == repair
    assert [call["label"] for call in context.calls] == [
        "frontend-developer", "regression-qa", "frontend-developer-repair"
    ]
    assert [call["budget"] for call in context.calls] == [30_000, 6_000, 18_000]


@pytest.mark.asyncio
async def test_resilient_dev_qa_reviews_stopped_developer_diff(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    context = FakeContext([None, "VERDICT: PASS\nThe diff supports the requirement."])

    result = await module.frontend_dev_qa_resilient(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["status"] == "ok"
    assert result["condition"] == "dev-qa-resilient"
    assert result["developer_outcome"]["status"] == "stopped"
    assert result["handoff_recovery"] == {"developer": True, "repair": False}
    assert result["qa"]["verdict"] == "PASS"
    assert [call["label"] for call in context.calls] == [
        "frontend-developer",
        "regression-qa",
    ]


@pytest.mark.asyncio
async def test_resilient_dev_qa_rejects_stopped_developer_without_diff(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())

    class EmptyDiffContext(FakeContext):
        async def diff(self):
            return ""

    context = EmptyDiffContext([None])
    result = await module.frontend_dev_qa_resilient(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["status"] == "incomplete"
    assert result["handoff_recovery"] == {"developer": False, "repair": False}
    assert [call["label"] for call in context.calls] == ["frontend-developer"]


@pytest.mark.asyncio
async def test_single_marks_missing_agent_report_incomplete(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    context = FakeContext([None])

    result = await module.frontend_single(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["status"] == "incomplete"
    assert result["developer"] is None
    assert result["tokens_spent"] == 321


@pytest.mark.asyncio
async def test_native_agent_run_preserves_budget_stop_reason(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())

    class StoppedContext(FakeContext):
        async def agent_run(self, prompt, **kwargs):
            result = await super().agent_run(prompt, **kwargs)
            self.sessions.append(
                SimpleNamespace(
                    state=SimpleNamespace(
                        phase=SimpleNamespace(value="stopped"),
                        terminal_reason="budget exhausted before model call",
                    )
                )
            )
            return result

    result = await module.frontend_single(
        StoppedContext([None]),
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["status"] == "incomplete"
    assert result["error"] == "budget exhausted before model call"
    assert result["developer_outcome"] == {
        "status": "stopped",
        "reason": "budget exhausted before model call",
        "tokens": 100,
        "steps": 2,
        "cleanup_complete": True,
        "workspace_ready": True,
    }


@pytest.mark.asyncio
async def test_status_aware_extension_preserves_structured_budget_stop_reason():
    from workflows.status_aware_agent import run_structured_agent_checked

    class StructuredStoppedContext(FakeContext):
        async def agent(self, prompt, **kwargs):
            result = await super().agent(prompt, **kwargs)
            self.sessions.append(
                SimpleNamespace(
                    state=SimpleNamespace(
                        phase=SimpleNamespace(value="stopped"),
                        terminal_reason="budget exhausted before model call",
                    )
                )
            )
            return result

    outcome = await run_structured_agent_checked(
        StructuredStoppedContext([None]),
        "Review regression risk",
        schema={"type": "object"},
    )

    assert outcome.as_dict() == {
        "output": None,
        "status": "stopped",
        "reason": "budget exhausted before model call",
        "sessions_started": 1,
    }


@pytest.mark.asyncio
async def test_frontend_verifier_runs_only_fixed_checks():
    from workflows.frontend_verify import FrontendVerifyTool

    class Environment:
        command = None

        async def exec_cmd(self, command, timeout):
            self.command = (command, timeout)
            return SimpleNamespace(
                returncode=0,
                stdout="build passed\n6 passed",
                stderr="",
                timed_out=False,
            )

    environment = Environment()
    output = await FrontendVerifyTool().execute_with_runtime(
        {},
        SimpleNamespace(environment=environment, observations=None),
    )

    assert environment.command == (
        "npm run verify:agent",
        300.0,
    )
    assert output == "Exit code: 0\nbuild passed\n6 passed"
