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


# ---------------------------------------------------------------------------
# 08 · Alertas tempranas (programado)
# ---------------------------------------------------------------------------
ALERTAS_PATH = WORKFLOW_DIR / "08_alertas.json"


def test_alertas_workflow_exists_with_key_nodes():
    assert ALERTAS_PATH.exists()
    workflow = _load(ALERTAS_PATH)
    assert workflow["id"] == "wfUnab08Alertas01"
    types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.scheduleTrigger" in types
    assert "n8n-nodes-base.splitInBatches" in types
    assert "@n8n/n8n-nodes-langchain.chainLlm" in types
    assert "@n8n/n8n-nodes-langchain.lmChatGoogleGemini" in types
    queries = " ".join(n["parameters"].get("query", "") for n in workflow["nodes"])
    assert "academico.v_alertas" in queries
    assert "ON CONFLICT (codigo, fecha) DO NOTHING" in queries
    assert "LIMIT 25" in queries


def test_alertas_workflow_credentials():
    workflow = _load(ALERTAS_PATH)
    for node in workflow["nodes"]:
        creds = node.get("credentials", {})
        if node["type"] == "n8n-nodes-base.postgres":
            assert creds["postgres"]["id"] == "credSupabaseUnab1"
        if node["type"] == "@n8n/n8n-nodes-langchain.lmChatGoogleGemini":
            assert creds["googlePalmApi"]["id"] == "credGeminiUnab01"
            assert node["parameters"]["modelName"] == "models/gemini-3.5-flash-lite"


def test_alertas_workflow_has_no_public_webhooks():
    workflow = _load(ALERTAS_PATH)
    assert not [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.webhook"]


def test_alertas_published_in_setup_script():
    script = (WORKFLOW_DIR.parents[0] / "setup_n8n.sh").read_text(encoding="utf-8")
    assert "wfUnab08Alertas01" in script
