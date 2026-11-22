from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_designbench import _task  # noqa: E402
from run_designbench_experiment import run_one  # noqa: E402


def test_designbench_manifest_pins_five_distinct_react_tasks():
    manifest = json.loads(
        (ROOT / "benchmark" / "designbench" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["revision"] == "a1e58d66ecbf1f77848bc5529ee7bbbe33bc25ba"
    assert manifest["dataset_revision"] == "a04022a331a8ad385dbbf26a1da9ca4a26a2628d"
    assert manifest["framework"] == "react"
    assert len(manifest["tasks"]) == 5
    assert len({task["id"] for task in manifest["tasks"]}) == 5
    assert {task["kind"] for task in manifest["tasks"]} == {"edit", "repair", "compile"}
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
