"""
Scraper periódico de noticias, nuevos cursos, convocatorias y certificaciones de la UNAB.

Estrategia robusta en dos niveles:
  1. API REST de WordPress de unab.edu.co (/wp-json/wp/v2/posts) por categorías y
     búsquedas clave → datos estructurados (id, fecha, título, enlace, contenido).
  2. Fallback HTML: si la API falla, parsea el listado HTML de las categorías.

Cada noticia se clasifica (curso / convocatoria / certificación / evento / general),
recibe un puntaje de relevancia para estudiantes de Ingeniería de Sistemas y se
hace UPSERT en chatbot.noticia. Opcionalmente (--embed) se vectoriza en el RAG.

Se ejecuta cada 12 h desde n8n (workflow 04) o con cron:
    0 */12 * * *  python scraper/scraper_noticias.py --embed
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

WP = "https://unab.edu.co/wp-json/wp/v2/posts"
HEADERS = {"User-Agent": "ChatbotAcademicoUNAB/1.0 (proyecto academico; scraping respetuoso)"}
CATEGORIAS = {556: "Ingeniería de Sistemas", 134: "Facultad de Ingeniería", 232: "Estudiantes",
              449: "Éxito estudiantil", 222: "Cursos", 430: "Educación continua"}
BUSQUEDAS = ["competencias digitales", "curso", "convocatoria", "certificación", "inteligencia artificial",
             "beca", "práctica", "hackathon", "semillero"]

REGLAS_TIPO = [
    ("certificación", r"certifica|insignia|diplomado|credencial"),
    ("curso", r"curso|taller|vacacional|intersemestral|ciclo|competencias digitales"),
    ("convocatoria", r"convocatoria|postula|inscrip|beca|premio|concurso|hackat"),
    ("evento", r"conferencia|seminario|coloquio|feria|encuentro|congreso|webinar"),
]
PALABRAS_RELEVANCIA = {
    r"sistemas|software|programaci|datos|inteligencia artificial|\bia\b|ciberseguridad|nube|cloud": 3.0,
    r"competencias digitales|interacci[oó]n digital|insignia|inform[aá]tica": 2.5,
    r"estudiantes|pregrado|matr[ií]cula|calendario|beca|pr[aá]ctica": 1.5,
    r"ingenier[ií]a": 1.0,
}
EXCLUIR = re.compile(r"^profesor|experto tem[aá]tico|gestor de|trabaja con nosotros|^profesional en", re.I)


def clasificar(texto: str) -> str:
    t = texto.lower()
    for tipo, patron in REGLAS_TIPO:
        if re.search(patron, t):
            return tipo
    return "general"


def relevancia(titulo: str, resumen: str, fecha: datetime) -> float:
    t = f"{titulo} {titulo} {resumen}".lower()  # el título pesa doble
    score = sum(w for p, w in PALABRAS_RELEVANCIA.items() if re.search(p, t))
    dias = (datetime.now(timezone.utc) - fecha).days
    return round(score * (0.5 ** (dias / 90)), 2)  # decaimiento con vida media de 90 días


def limpiar(h: str) -> str:
    txt = BeautifulSoup(h or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", html.unescape(txt)).strip()


def desde_api(dias: int) -> list[dict]:
    after = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S")
    base = {"per_page": 20, "after": after, "_fields": "id,date_gmt,link,title,excerpt,content,categories"}
    posts: dict[int, dict] = {}
    for cid, nombre in CATEGORIAS.items():
        r = requests.get(WP, params={**base, "categories": cid}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        for p in r.json():
            posts.setdefault(p["id"], {**p, "_cat": nombre})
    for q in BUSQUEDAS:
        r = requests.get(WP, params={**base, "search": q}, headers=HEADERS, timeout=30)
        if r.ok:
            for p in r.json():
                posts.setdefault(p["id"], {**p, "_cat": f"búsqueda: {q}"})
    out = []
    for p in posts.values():
        titulo = limpiar(p["title"]["rendered"])
        if EXCLUIR.search(titulo):
            continue
        fecha = datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc)
        resumen = limpiar(p["excerpt"]["rendered"])[:600]
        contenido = limpiar(p["content"]["rendered"])[:8000]
        out.append(dict(noticia_id=p["id"], titulo=titulo, url=p["link"], fecha_pub=fecha, categoria=p["_cat"],
                        tipo=clasificar(f"{titulo} {resumen}"), resumen=resumen, contenido=contenido,
                        relevancia=relevancia(titulo, resumen, fecha)))
    return out


def desde_html() -> list[dict]:
    """Fallback: parsea el listado HTML de la categoría Estudiantes."""
    r = requests.get("https://unab.edu.co/category/estudiantes/", headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for art in soup.select("article"):
        a = art.find("a", href=True)
        h = art.find(re.compile("h[1-4]"))
        if not a or not h:
            continue
        titulo = h.get_text(strip=True)
        fecha = datetime.now(timezone.utc)
        t = art.find("time")
        if t and t.get("datetime"):
            fecha = datetime.fromisoformat(t["datetime"].replace("Z", "+00:00"))
        resumen = art.get_text(" ", strip=True)[:500]
        out.append(dict(noticia_id=abs(hash(a["href"])) % 10**9, titulo=titulo, url=a["href"], fecha_pub=fecha,
                        categoria="Estudiantes (HTML)", tipo=clasificar(titulo), resumen=resumen, contenido=resumen,
                        relevancia=relevancia(titulo, resumen, fecha)))
    return out


def guardar(noticias: list[dict], embed: bool) -> tuple[int, int]:
    import psycopg

    nuevas = 0
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, extensions")
        for n in noticias:
            cur.execute(
                """INSERT INTO chatbot.noticia (noticia_id, titulo, url, fecha_pub, categoria, tipo, resumen, contenido, relevancia)
                   VALUES (%(noticia_id)s, %(titulo)s, %(url)s, %(fecha_pub)s, %(categoria)s, %(tipo)s, %(resumen)s, %(contenido)s, %(relevancia)s)
                   ON CONFLICT (noticia_id) DO UPDATE SET relevancia = EXCLUDED.relevancia, scrapeado_en = now()
                   RETURNING (xmax = 0) AS insertada""", n)
            if cur.fetchone()[0]:
                nuevas += 1
                if embed and n["relevancia"] >= 1.0:
                    vectorizar(cur, n)
        conn.commit()
    return len(noticias), nuevas


_GENAI = None


def vectorizar(cur, n: dict) -> None:
    from google import genai
    from google.genai import types

    texto = f"Noticia UNAB ({n['fecha_pub']:%Y-%m-%d}): {n['titulo']}\n{n['contenido'][:1800]}"
    global _GENAI
    if _GENAI is None:
        _GENAI = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    v = _GENAI.models.embed_content(
        model=os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001"), contents=texto,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")).embeddings[0].values
    md = {"titulo": n["titulo"], "url": n["url"], "fuente": "Noticias UNAB", "origen": "noticia",
          "fecha": n["fecha_pub"].date().isoformat()}
    cur.execute("INSERT INTO chatbot.rag_documentos (text, metadata, embedding) VALUES (%s, %s::jsonb, %s::vector)",
                (texto, json.dumps(md, ensure_ascii=False), "[" + ",".join(map(str, v)) + "]"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=180, help="ventana de búsqueda hacia atrás")
    ap.add_argument("--embed", action="store_true", help="vectorizar noticias nuevas en el RAG")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        data = desde_api(a.dias)
        origen = "API WordPress"
    except Exception as exc:
        print("API no disponible, usando fallback HTML:", exc)
        data, origen = desde_html(), "HTML"
    data.sort(key=lambda n: -n["relevancia"])
    print(f"{len(data)} noticias obtenidas vía {origen}")
    for n in data[:8]:
        print(f"  [{n['tipo']:<13}] {n['relevancia']:>5}  {n['fecha_pub']:%Y-%m-%d}  {n['titulo'][:80]}")
    if not a.dry_run:
        total, nuevas = guardar(data, a.embed)
        print(f"Guardadas {total} ({nuevas} nuevas)")
