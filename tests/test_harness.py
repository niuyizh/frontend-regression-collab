from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import task_record  # noqa: E402
from run_experiment import _extract_json  # noqa: E402
from run_matrix import matrix  # noqa: E402


def _workflow_module():
    path = ROOT / "workflows" / "frontend_agents.py"
    spec = importlib.util.spec_from_file_location("frontend_agents_under_test", path)
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


def test_cli_json_extraction_prefers_final_payload():
    text = 'log with {embedded: braces}\n{"status": "ok", "tokens_spent": 42}\n'
    assert _extract_json(text) == {"status": "ok", "tokens_spent": 42}


def test_qa_tool_bundle_has_no_write_tool():
    module = _workflow_module()
    names = {tool.name for tool in module._qa_tools(True)}
    assert names == {"bash", "file_read", "grep", "git_diff"}
    assert "apply_patch" not in names


class FakeContext:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.phases = []
        self.agent_failures = ()

    async def phase(self, name):
        self.phases.append(name)

    async def agent(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return next(self.replies)

    async def diff(self):
        return "diff --git a/src/App.tsx b/src/App.tsx"

    def tokens_spent(self):
        return 321


@pytest.mark.asyncio
async def test_dev_qa_skips_repair_on_pass(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    monkeypatch.setattr(module, "_qa_tools", lambda _allow: ())
    developer = {"summary": "done", "tests_run": [], "known_risks": []}
    qa = {"verdict": "PASS", "findings": [], "checks_run": [], "coverage_note": "checked"}
    context = FakeContext([developer, qa])

    result = await module.frontend_dev_qa(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["repair"] is None
    assert [call["label"] for call in context.calls] == ["frontend-developer", "regression-qa"]
    assert [call["budget"] for call in context.calls] == [10_000, 3_000]


@pytest.mark.asyncio
async def test_dev_qa_uses_one_bounded_repair_on_fail(monkeypatch):
    module = _workflow_module()
    monkeypatch.setattr(module, "_developer_tools", lambda _allow: ())
    monkeypatch.setattr(module, "_qa_tools", lambda _allow: ())
    developer = {"summary": "done", "tests_run": [], "known_risks": []}
    qa = {
        "verdict": "FAIL",
        "findings": [{"severity": "major", "behavior": "x", "evidence": "y", "reproduction": "z", "suggested_fix": "w"}],
        "checks_run": [],
        "coverage_note": "checked",
    }
    repair = {"summary": "fixed", "tests_run": ["npm test"], "known_risks": []}
    context = FakeContext([developer, qa, repair])

    result = await module.frontend_dev_qa(
        context,
        {"goal": "Implement feature", "allow_unisolated_shell": True},
    )

    assert result["repair"] == repair
    assert [call["label"] for call in context.calls] == [
        "frontend-developer", "regression-qa", "frontend-developer-repair"
    ]
    assert [call["budget"] for call in context.calls] == [10_000, 3_000, 3_000]


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
