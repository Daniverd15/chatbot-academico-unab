import ast
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

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


# ---------------------------------------------------------------------------
# 05 / 05b · Noticias multifuente (sin importar el scraper ni cargar .env)
# ---------------------------------------------------------------------------
def _scraper_definitions():
    tree = ast.parse((WORKFLOW_DIR.parents[1] / "scraper" / "scraper_noticias.py").read_text(encoding="utf-8"))
    return {node.targets[0].id: node.value for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}


def _run_code(node, items=(), sources=()):
    # Node es opcional para los chequeos estructurales, necesario para ejecutar el JS real.
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Node.js no disponible para ejecutar el Code node de n8n")
    harness = r"""const fs = require('node:fs');
const {code, items, sources} = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = new Function('$input', '$', code)(
  {all: () => items}, name => {
    if (name !== 'Fuentes RSS') throw new Error('Referencia inesperada: ' + name);
    return {itemMatching: i => ({json: sources[i]})};
  });
process.stdout.write(JSON.stringify(result));"""
    result = subprocess.run([executable, "-e", harness],
                            input=json.dumps({"code": node["parameters"]["jsCode"], "items": items, "sources": sources}),
                            text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


def test_rss_download_branch_and_sources_match_scraper():
    workflow = _load(WORKFLOW_DIR / "05b_scraper.json")
    nodes = {n["name"]: n for n in workflow["nodes"]}
    http = nodes["Descargar feeds RSS"]
    assert http["type"] == "n8n-nodes-base.httpRequest"
    assert http["onError"] == "continueRegularOutput"
    assert nodes["API WordPress UNAB"]["onError"] == "continueRegularOutput"
    response = http["parameters"]["options"]["response"]["response"]
    assert response == {"responseFormat": "text", "outputPropertyName": "xml"}
    assert http["parameters"]["url"] == "={{ $json.url }}"
    assert nodes["Cada 12 horas"]["parameters"]["rule"]["interval"][0]["hoursInterval"] == 12
    branch = ["Cada 12 horas", "Fuentes RSS", "Descargar feeds RSS", "Parsear y clasificar RSS", "UPSERT noticia RSS"]
    for src, dst in zip(branch, branch[1:]):
        assert any(c["node"] == dst for c in workflow["connections"][src]["main"][0])
    definitions = _scraper_definitions()
    expected = []
    for row in definitions["FUENTES_RSS"].elts:
        name, url, hint, aggregator = row.elts
        if isinstance(url, ast.Call):
            assert isinstance(url.func, ast.Name) and url.func.id == "_gn"
            url = ast.literal_eval(definitions["GNEWS"]).replace("{q}", quote(ast.literal_eval(url.args[0])))
        else:
            url = ast.literal_eval(url)
        expected.append({"nombre": ast.literal_eval(name), "url": url.replace("{d}", "3"),
                         "tema": ast.literal_eval(hint), "agregador": ast.literal_eval(aggregator)})
    assert [i["json"] for i in _run_code(nodes["Fuentes RSS"])] == expected


def test_news_upserts_and_response_keep_topics_and_sources():
    nodes = {n["name"]: n for n in _load(WORKFLOW_DIR / "05b_scraper.json")["nodes"]}
    for name, conflict in [("UPSERT noticia", "noticia_id"), ("UPSERT noticia RSS", "url")]:
        node = nodes[name]
        query = node["parameters"]["query"]
        assert f"ON CONFLICT ({conflict}) DO UPDATE" in query
        assert "tema, fuente_nombre)" in query.split("VALUES")[0]
        for column in ("tema", "fuente_nombre", "relevancia"):
            assert f"{column} = EXCLUDED.{column}" in query
            assert f"$json.{column}" in node["parameters"]["options"]["queryReplacement"]
        assert "scrapeado_en = now()" in query
        assert node["credentials"]["postgres"]["id"] == "credSupabaseUnab1"
    response = {n["name"]: n for n in _load(WORKFLOW_DIR / "05_noticias.json")["nodes"]}
    query = response["Noticias recientes"]["parameters"]["query"]
    assert "tipo, tema, fuente_nombre" in query
    assert "interval '7 days'" in query
    assert "PARTITION BY reciente, coalesce(tema" in query
    assert "ORDER BY reciente DESC, turno_tema" in query
    prompt = response["Redactar novedades"]["parameters"]["messages"]["messageValues"][0]["message"]
    assert "cita el medio (fuente_nombre) y la fecha de publicación" in prompt


def test_rss_parser_filters_deduplicates_and_matches_python_rules_and_sha1():
    nodes = {n["name"]: n for n in _load(WORKFLOW_DIR / "05b_scraper.json")["nodes"]}
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    old = (now - timedelta(days=4)).isoformat()
    future = (now + timedelta(days=1)).isoformat()

    def item(title, url, date=recent, source="Medio & Ciencia", description=""):
        return (f"<item><title><![CDATA[{title}]]></title><link>{escape(url)}</link>"
                f"<pubDate>{date}</pubDate><description><![CDATA[{description}]]></description>"
                f'<source url="https://medio.test">{escape(source)}</source></item>')

    url = "https://medio.test/ingeniería/🧪?a=1&b=2"
    xml = "<rss><channel>" + "".join([
        item("Ingeniería de software y Python - Medio &amp; Ciencia", url),
        item("Ingeniería de software y Python - Medio &amp; Ciencia", "https://duplicate.test"),
        item("Otro titular de software", url),
        item("Educación superior antigua", "https://old.test", old),
        item("Tecnología del futuro", "https://future.test", future),
        item("Software sin fecha", "https://nodate.test", ""),
        item("Software social - YouTube", "https://social.test", source="YouTube"),
        item("Ofertas de tecnología", "https://offer.test"),
        item("Tema sin palabras clave", "https://hint.test"),
    ]) + "</channel></rss>"
    direct = "<rss>" + item("Educación universitaria y becas", "https://education.test",
                             description="<p>Recursos para estudiantes.</p> Leer más") + item(
        "Cocina de temporada", "https://unrelated.test") + "</rss>"
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>ChatGPT y tecnología</title>'
            '<link href="https://atom.test/ia?a=1&amp;b=2"/><updated>' + (now - timedelta(hours=1)).isoformat()
            + '</updated><summary>Internet digital</summary></entry></feed>')
    sources = [{"nombre": "Caído", "tema": "tecnologia", "agregador": False},
               {"nombre": "Google News", "tema": "ingenieria_sistemas", "agregador": True},
               {"nombre": "Medio educativo", "tema": "educacion", "agregador": False},
               {"nombre": "Medio Atom", "tema": "tecnologia", "agregador": False}]
    data = _run_code(nodes["Parsear y clasificar RSS"],
                     [{"json": {"error": "timeout"}}, {"json": {"xml": xml}},
                      {"json": {"xml": direct}}, {"json": {"xml": atom}}], sources)
    news = [i["json"] for i in data]
    assert [n["url"] for n in news] == [url, "https://hint.test", "https://education.test", "https://atom.test/ia?a=1&b=2"]
    assert [n["tema"] for n in news] == ["ingenieria_sistemas", "ingenieria_sistemas", "educacion", "tecnologia"]
    assert news[0]["titulo"] == "Ingeniería de software y Python"
    assert news[0]["fuente_nombre"] == "Medio & Ciencia"
    assert news[0]["resumen"] == ""
    assert news[2]["resumen"] == "Recursos para estudiantes."
    assert news[2]["fuente_nombre"] == "Medio educativo"
    assert [n["pairedItem"]["item"] for n in data] == [1, 1, 2, 3]
    for n in news:
        assert n["noticia_id"] == 10**12 + int(hashlib.sha1(n["url"].encode()).hexdigest()[:10], 16)
        assert n["relevancia"] >= 0.5

    # Compara todas las reglas y desempates con las funciones Python, sin ejecutar imports/load_dotenv.
    tree = ast.parse((WORKFLOW_DIR.parents[1] / "scraper" / "scraper_noticias.py").read_text(encoding="utf-8"))
    scope = {"re": re}
    scope.update({name: ast.literal_eval(value) for name, value in _scraper_definitions().items()
                  if name in {"TEMAS", "TEMA_HINT_BONUS"}})
    for function in tree.body:
        if isinstance(function, ast.FunctionDef) and function.name in {"puntaje_temas", "clasificar_tema"}:
            exec(compile(ast.Module(body=[function], type_ignores=[]), "scraper_rules", "exec"), scope)
    cases = [("Aviso UNAB para estudiantes", "", None, True),
             ("Ingeniería de software y Python", "", None, True),
             ("Educación universitaria", "", None, True),
             ("Sin términos", "", "educacion", False),
             ("Software y tecnología", "", "tecnologia", False),
             ("Educación", "software y Python", "ingenieria_sistemas", False)]
    # Cada patrón aparece como resumen y como titular, con cada hint y umbral institucional.
    for rules in scope["TEMAS"].values():
        for pattern, _ in rules:
            for word in re.split(r"\||\\b", pattern):
                if re.fullmatch(r"[\w ]+", word):
                    cases.extend((title, summary, hint, institutional)
                                 for title, summary in [(word, ""), ("Aviso", word)]
                                 for hint in [None, *scope["TEMAS"]] for institutional in [False, True])
    common_js = nodes["Parsear y clasificar RSS"]["parameters"]["jsCode"].split("// SHA-1 puro")[0]
    probe = {"parameters": {"jsCode": common_js + "\nreturn " + json.dumps(cases, ensure_ascii=False)
                            + ".map(c => clasificarTema(...c));"}}
    assert _run_code(probe) == [scope["clasificar_tema"](*case) for case in cases]
