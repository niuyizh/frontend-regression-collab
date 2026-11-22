"""Download the five pinned DesignBench task records and minimal assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT

ADAPTER_ROOT = PROJECT_ROOT / "benchmark" / "designbench"
DATA_ROOT = ADAPTER_ROOT / "data"
MANIFEST_PATH = ADAPTER_ROOT / "manifest.json"


def _download(
    relative: str,
    destination: Path,
    *,
    force: bool,
    base_url: str,
) -> dict[str, Any]:
    if force or not destination.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            f"{base_url}/{relative}",
            headers={"User-Agent": "frontend-regression-collab/1"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)
    payload = destination.read_bytes()
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def fetch(*, force: bool = False) -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    dataset_revision = manifest["dataset_revision"]
    dataset = manifest["dataset"]
    base_url = f"https://huggingface.co/datasets/{dataset}/resolve/{dataset_revision}"
    files: list[dict[str, Any]] = []
    for task in manifest["tasks"]:
        kind = task["kind"]
        source_id = task["source_id"]
        prefix = f"{kind}/react/{source_id}"
        metadata_relative = f"{prefix}/{source_id}.json"
        metadata_path = DATA_ROOT / metadata_relative
        files.append(
            _download(metadata_relative, metadata_path, force=force, base_url=base_url)
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))

        if kind == "edit":
            asset_names = [f"{metadata['src_id']}.png", f"{metadata['dst_id']}.png"]
        elif kind == "repair":
            asset_names = [
                f"{source_id}.png",
                f"{source_id}_mark.png",
                "repaired.json",
                "repaired.jsx",
                "repaired.png",
            ]
        else:
            asset_names = [f"{source_id}.jsx", "repaired.jsx"]

        for name in asset_names:
            relative = f"{prefix}/{name}"
            files.append(
                _download(relative, DATA_ROOT / relative, force=force, base_url=base_url)
            )

    record = {
        "schema_version": 1,
        "benchmark": manifest["benchmark"],
        "revision": manifest["revision"],
        "dataset": manifest["dataset"],
        "dataset_revision": dataset_revision,
        "files": files,
    }
    output = DATA_ROOT / "download-manifest.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = fetch(force=args.force)
    print(json.dumps({"files": len(result["files"]), "bytes": sum(item["bytes"] for item in result["files"])}, indent=2))


if __name__ == "__main__":
    main()
