import json
import re
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parents[1] / "n8n" / "workflows"
WORKFLOW_FILES = sorted(WORKFLOW_DIR.glob("*.json"))

SECRET_PATTERN = re.compile(r"AIza|eyJ|sk-[A-Za-z0-9_-]{20,}")


def _load(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_node_names_are_unique(path):
    workflow = _load(path)
    names = [node["name"] for node in workflow["nodes"]]
    duplicates = {name for name in names if names.count(name) > 1}
    assert not duplicates, f"{path.name} has duplicate node names: {sorted(duplicates)}"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_connection_targets_exist(path):
    workflow = _load(path)
    node_names = {node["name"] for node in workflow["nodes"]}
    missing = set()

    for outputs in workflow.get("connections", {}).values():
        for branches in outputs.values():
            for branch in branches:
                for connection in branch:
                    target = connection["node"]
                    if target not in node_names:
                        missing.add(target)

    assert not missing, f"{path.name} connects to missing nodes: {sorted(missing)}"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_execute_workflow_references_existing_workflow(path):
    workflow_ids = {_load(item)["id"] for item in WORKFLOW_FILES}
    workflow = _load(path)
    missing = []

    for node in workflow["nodes"]:
        if node.get("type") != "n8n-nodes-base.executeWorkflow":
            continue

        reference = node.get("parameters", {}).get("workflowId")
        if isinstance(reference, dict):
            reference = reference.get("value")

        if not reference or reference not in workflow_ids:
            missing.append((node["name"], reference))

    assert not missing, f"{path.name} has invalid executeWorkflow references: {missing}"


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=lambda p: p.name)
def test_no_secret_like_strings(path):
    text = path.read_text(encoding="utf-8")
    match = SECRET_PATTERN.search(text)
    assert match is None, f"{path.name} contains a secret-like string: {match.group(0)!r}"
