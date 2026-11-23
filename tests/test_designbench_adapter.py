from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_designbench import _task  # noqa: E402
from run_designbench_experiment import run_one  # noqa: E402
from score_designbench import _progress  # noqa: E402
from summarize_designbench import FROZEN_REPETITIONS, summarize  # noqa: E402
from summarize_designbench_pilot import summarize as summarize_pilot  # noqa: E402


def test_designbench_manifest_pins_five_distinct_react_tasks():
    manifest = json.loads(
        (ROOT / "benchmark" / "designbench" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["revision"] == "a1e58d66ecbf1f77848bc5529ee7bbbe33bc25ba"
    assert manifest["dataset_revision"] == "a04022a331a8ad385dbbf26a1da9ca4a26a2628d"
    assert manifest["framework"] == "react"
    assert manifest["mode"] == "code"
    assert len(manifest["tasks"]) == 5
    assert len({task["id"] for task in manifest["tasks"]}) == 5
    assert {task["kind"] for task in manifest["tasks"]} == {"edit", "compile"}
    assert "db-e30" in {task["id"] for task in manifest["tasks"]}
    assert "db-r20" not in {task["id"] for task in manifest["tasks"]}
    for task in manifest["tasks"]:
        assert (ROOT / "benchmark" / "designbench" / task["prompt_file"]).is_file()
        assert _task(task["id"])["source_id"] == task["source_id"]


def test_agent_prompts_do_not_expose_gold_assets():
    prompt_dir = ROOT / "benchmark" / "designbench" / "prompts"
    for prompt in prompt_dir.glob("*.md"):
        text = prompt.read_text(encoding="utf-8").lower()
        assert "repaired.jsx" not in text
        assert "target.png" not in text
        assert "gold" not in text


def test_designbench_experiment_defaults_to_no_paid_execution():
    result = run_one(
        "db-e11",
        "dev-qa",
        1,
        opencollab_root=ROOT.parent / "code-assistant" / "OpenCollab",
        execute=False,
        force=False,
    )
    assert result["status"] == "dry-run"
    assert result["budget"] == 48_000
    assert result["workflow"] == "frontend-dev-qa"
    assert "--execute" not in result["command"]


def test_resilient_condition_selects_artifact_first_workflow(monkeypatch):
    import run_experiment as frontend_experiment  # noqa: PLC0415

    monkeypatch.setattr(
        frontend_experiment,
        "require_command",
        lambda name: f"/fake/{name}",
    )

    result = frontend_experiment.run_one(
        "t04-responsive-nav",
        "dev-qa-resilient",
        1,
        opencollab_root=ROOT.parent / "code-assistant" / "OpenCollab",
        execute=False,
        force=False,
    )
    assert result["workflow"] == "frontend-dev-qa-resilient"
    assert result["budget"] == 48_000


def test_designbench_resilient_condition_selects_artifact_first_workflow(monkeypatch):
    import run_designbench_experiment as experiment  # noqa: PLC0415

    monkeypatch.setattr(experiment, "require_command", lambda name: f"/fake/{name}")
    result = experiment.run_one(
        "db-e11",
        "dev-qa-resilient",
        1,
        opencollab_root=ROOT.parent / "code-assistant" / "OpenCollab",
        execute=False,
        force=False,
    )
    assert result["workflow"] == "frontend-dev-qa-resilient"
    assert result["budget"] == 48_000


def test_four_task_pilot_summary_uses_real_paired_runs():
    result = summarize_pilot()
    assert len(result["runs"]) == 8
    assert result["conditions"]["single"]["agent_valid"] == 4
    assert result["conditions"]["dev-qa-resilient"]["agent_valid"] == 3
    assert result["conditions"]["single"]["task_passed"] == 1
    assert result["conditions"]["dev-qa-resilient"]["task_passed"] == 1


def test_visual_calibration_covers_every_edit_and_separates_initial_from_gold():
    manifest = json.loads(
        (ROOT / "benchmark" / "designbench" / "manifest.json").read_text(encoding="utf-8")
    )
    scoring = json.loads(
        (ROOT / "benchmark" / "designbench" / "scoring.json").read_text(encoding="utf-8")
    )
    edit_ids = {task["id"] for task in manifest["tasks"] if task["kind"] == "edit"}
    assert set(scoring["calibration"]) == edit_ids
    for task_id in edit_ids:
        calibration = scoring["calibration"][task_id]
        assert calibration["initial"][scoring["metric"]] < calibration["gold"][scoring["metric"]]
        assert calibration["initial"]["structural_passed"] is False
        assert calibration["gold"]["structural_passed"] is True


def test_visual_progress_is_relative_to_frozen_initial_and_gold():
    assert _progress(0.2, 0.2, 0.8) == 0
    assert _progress(0.5, 0.2, 0.8) == pytest.approx(0.5)
    assert _progress(0.8, 0.2, 0.8) == 1


def test_frozen_designbench_pair_has_three_valid_repetitions():
    summary = summarize(ROOT / "results" / "designbench" / "raw")
    assert FROZEN_REPETITIONS == (2, 3, 4)
    assert len(summary["runs"]) == 6
    assert summary["conditions"]["single"]["valid_runs"] == 3
    assert summary["conditions"]["dev-qa"]["valid_runs"] == 3
    assert summary["conditions"]["single"]["task_passes"] == 2
    assert summary["conditions"]["dev-qa"]["task_passes"] == 3
    assert summary["mechanism_observation"]["repairs_triggered"] == 1
