"""
Construye el corpus institucional para el RAG a partir de fuentes públicas UNAB.

- Páginas del Centro de Competencias Digitales (CCD), prueba diagnóstica, insignia,
  cursos vacacionales, información del programa → vía API REST de WordPress de unab.edu.co
- Reglamento Estudiantil de Pregrado 2019 (PDF)
- Documentos propios del programa (plan de estudios simulado, preguntas frecuentes)

Salida: rag/corpus/md/*.md con front-matter (titulo, url, fuente, fecha).
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "corpus" / "md"
PDF_DIR = ROOT / "corpus" / "pdf"
WP = "https://unab.edu.co/wp-json/wp/v2"
HEADERS = {"User-Agent": "ChatbotAcademicoUNAB/1.0 (proyecto academico)"}

# slugs de entradas relevantes del CCD y del programa
SLUGS = [
    "asi-funciona-la-formacion-en-competencias-digitales-de-la-unab",
    "cursos-de-informatica-unab-cambian-a-partir-de-2026",
    "inscripcion-a-las-pruebas-diagnostica-de-competencias-digitales-primer-ingreso-solo-presenciales",
    "inscripcion-a-las-pruebas-diagnostica-de-competencias-digitales-primer-ingreso-solo-virtuales",
    "proximamente-cursos-vacacionales-de-competencias-digitales-unab",
    "estudiante-unab-solicita-tu-insignia-digital",
    "pruebas-de-informatica",
    "ingenieria-de-sistemas-unab-ahora-presencial-y-virtual",
]
RELEVANTE = re.compile(r"competencias|inform[aá]tica|interacci[oó]n digital|insignia|ingenier[ií]a de sistemas|intersemestral|vacacional|transformaci[oó]n digital")
EXCLUIR = re.compile(r"profesor|experto|gestor|profesional en|convocatoria docente")
BUSQUEDAS = ["competencias digitales", "cursos de informática", "insignia digital", "ingeniería de sistemas", "intersemestral"]


def limpiar_html(h: str) -> str:
    soup = BeautifulSoup(h, "html.parser")
    for t in soup(["script", "style", "figure", "iframe"]):
        t.decompose()
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for h_ in soup.find_all(re.compile("^h[1-6]$")):
        h_.insert_before("\n\n## ")
        h_.insert_after("\n")
    txt = html.unescape(soup.get_text(" "))
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n\n", txt)
    return txt.strip()


def guardar(nombre: str, titulo: str, url: str, fuente: str, fecha: str, cuerpo: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fm = json.dumps({"titulo": titulo, "url": url, "fuente": fuente, "fecha": fecha}, ensure_ascii=False)
    (OUT / f"{nombre}.md").write_text(f"---\n{fm}\n---\n# {titulo}\n\n{cuerpo}\n", encoding="utf-8")
    print(f"  ✓ {nombre}.md ({len(cuerpo):,} caracteres)")


def post_a_md(p: dict, fuente: str) -> None:
    titulo = html.unescape(BeautifulSoup(p["title"]["rendered"], "html.parser").get_text())
    cuerpo = limpiar_html(p["content"]["rendered"])
    if len(cuerpo) < 200:
        return
    guardar(f"{p['slug'][:70]}-{p['id']}", titulo, p["link"], fuente, p["date"][:10], cuerpo)


def wordpress() -> None:
    vistos = set()
    for slug in SLUGS:
        for tipo in ("posts", "pages"):
            r = requests.get(f"{WP}/{tipo}", params={"slug": slug}, headers=HEADERS, timeout=30)
            if r.ok and r.json():
                p = r.json()[0]
                vistos.add(p["id"])
                post_a_md(p, "Centro de Competencias Digitales UNAB" if "competencias" in slug or "insignia" in slug
                          or "informatica" in slug else "UNAB")
                break
    for q in BUSQUEDAS:
        r = requests.get(f"{WP}/posts", params={"search": q, "per_page": 6}, headers=HEADERS, timeout=30)
        for p in r.json() if r.ok else []:
            titulo = p["title"]["rendered"].lower()
            if p["id"] not in vistos and RELEVANTE.search(titulo) and not EXCLUIR.search(titulo):
                vistos.add(p["id"])
                post_a_md(p, "Noticias UNAB")


def reglamento() -> None:
    pdf = PDF_DIR / "reglamento_estudiantil_pregrado_2019.pdf"
    if not pdf.exists():
        return
    texto = "\n".join((pg.extract_text() or "") for pg in PdfReader(pdf).pages)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n(\d{1,2})\s*\n", "\n", texto)            # números de página
    texto = re.sub(r"(ARTÍCULO \d+\.)", r"\n\n\1", texto)        # cada artículo en su párrafo
    texto = re.sub(r"(CAPÍTULO [A-ZÉÍÓÚ]+:?)", r"\n\n## \1", texto)
    guardar("reglamento_estudiantil_pregrado_2019", "Reglamento Estudiantil de Pregrado UNAB (2019)",
            "https://unab.edu.co/NewFolder/Reglamento-estudiantil-pregraod.pdf",
            "Reglamento Estudiantil", "2019-01-01", texto)


def plan_estudios() -> None:
    sys.path.insert(0, str(ROOT.parent / "database"))
    from catalogo import CD_CURSOS, CURSOS, PROGRAMA, REQUISITOS_GRADO  # noqa: E402

    nombres = {c[0]: c[1] for c in CURSOS}
    lineas = [
        f"Programa: {PROGRAMA['nombre']} — {PROGRAMA['facultad']}. Código SNIES {PROGRAMA['snies']}. "
        f"Modalidad {PROGRAMA['modalidad']}. Duración: 8 semestres académicos más un semestre de práctica "
        f"profesional. Total de créditos del plan: {PROGRAMA['creditos_totales']}. Carga máxima por semestre: "
        f"{PROGRAMA['max_creditos_sem']} créditos. Título: {PROGRAMA['titulo_otorgado']}.",
        "Nota: este plan de estudios es una simulación académica para el proyecto del chatbot.",
    ]
    for s in range(1, 10):
        cs = [c for c in CURSOS if c[3] == s]
        lineas.append(f"\n## Semestre {s} ({sum(c[2] for c in cs)} créditos)")
        for c in cs:
            pre = [nombres.get(p, p.replace("CRED:", "mínimo ") + (" créditos aprobados" if p.startswith("CRED") else ""))
                   for p in c[8]]
            lineas.append(f"- {c[1]} ({c[0]}): {c[2]} créditos, componente {c[4]}, área {c[5]}. "
                          f"Prerrequisitos: {', '.join(pre) if pre else 'ninguno'}.")
    lineas.append("\n## Requisitos de grado")
    for r in REQUISITOS_GRADO:
        lineas.append(f"- {r[1]}: {r[2]}")
    lineas.append("\n## Ruta de Competencias Digitales (CCD)")
    for c in CD_CURSOS:
        eq = f" Se homologa por {c[7]}." if c[7] else ""
        lineas.append(f"- {c[1]} — Ruta {c[2]} ({c[3]}), {c[4]} horas, {c[5]}. {c[8]}{eq}")
    guardar("plan_estudios_ingenieria_sistemas", "Plan de estudios de Ingeniería de Sistemas (simulado)",
            "https://unab.edu.co/programas/ingenieria-de-sistemas/", "Programa de Ingeniería de Sistemas",
            "2026-08-01", "\n".join(lineas))


if __name__ == "__main__":
    print("Descargando corpus institucional…")
    wordpress()
    reglamento()
    plan_estudios()
    print("Listo →", OUT)
