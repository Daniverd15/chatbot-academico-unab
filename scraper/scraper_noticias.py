"""
Scraper periódico multifuente: noticias del día sobre educación, tecnología e ingeniería de
sistemas, más las noticias, cursos, convocatorias y certificaciones de la UNAB.

Fuentes:
  1. UNAB · API REST de WordPress de unab.edu.co (/wp-json/wp/v2/posts) por categorías y
     búsquedas clave; si la API falla, fallback que parsea el listado HTML.
  2. RSS públicos en español (FUENTES_RSS): Google News (es-419, Colombia) con consultas
     temáticas y feeds de medios de tecnología y educación. Se parsean con xml.etree
     (RSS 2.0 y Atom), sin dependencias nuevas.

Cada noticia recibe un tipo (curso / convocatoria / certificación / evento / general), un
tema (educacion / tecnologia / ingenieria_sistemas / institucional), el nombre del medio
(fuente_nombre), la fecha real de publicación y un puntaje de relevancia; se deduplica por
URL (y por titular) y se hace UPSERT en chatbot.noticia. Con --embed se vectoriza en el RAG.

Uso (cada 12 h por cron o n8n):
    0 */12 * * *  python scraper/scraper_noticias.py --embed
    python scraper/scraper_noticias.py --dias 3 --dry-run     # solo mostrar
    python scraper/scraper_noticias.py --fuentes rss          # solo RSS externos
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

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

# ---------------------------------------------------------------------------
# Fuentes RSS externas (probadas: responden 200 con RSS 2.0 válido)
# ---------------------------------------------------------------------------
GNEWS = "https://news.google.com/rss/search?q={q}+when:{d}d&hl=es-419&gl=CO&ceid=CO:es-419"


def _gn(consulta: str) -> str:
    return GNEWS.replace("{q}", quote(consulta))


# (nombre, url, tema sugerido, ¿agregador?) — en Google News el medio real sale de <source>
FUENTES_RSS = [
    ("Google News", _gn('"ingeniería de sistemas" OR "ingeniería de software" OR programadores Colombia'),
     "ingenieria_sistemas", True),
    ("Google News", _gn('"desarrollo de software" OR ciberseguridad OR "ciencia de datos" Colombia'),
     "ingenieria_sistemas", True),
    ("Google News", _gn('"educación superior" Colombia'), "educacion", True),
    ("Google News", _gn('universidades OR estudiantes OR Mineducación Colombia educación'), "educacion", True),
    ("Google News", _gn('tecnología "inteligencia artificial"'), "tecnologia", True),
    ("Semana · Educación", "https://www.semana.com/arc/outboundfeeds/rss/category/educacion/?outputType=xml",
     "educacion", False),
    ("El Tiempo · Tecnósfera", "https://www.eltiempo.com/rss/tecnosfera.xml", "tecnologia", False),
    ("ENTER.CO", "https://www.enter.co/feed/", "tecnologia", False),
    ("Impacto TIC", "https://impactotic.co/feed/", "tecnologia", False),
    ("Xataka", "https://feeds.weblogssl.com/xataka2", "tecnologia", False),
    ("WWWhat's new", "https://wwwhatsnew.com/feed/", "tecnologia", False),
]
MAX_POR_FUENTE = 15
# Notas comerciales o de estilo de vida que publican los medios generalistas de tecnología
COMERCIAL = re.compile(r"black friday|cyber monday|\bofertas?\b|descuento|rebaja|cup[oó]n|a este precio|"
                       r"precio m[aá]s bajo|\bprecio m[ií]nimo|chollo", re.I)
NO_MEDIOS = re.compile(r"^(facebook|youtube|instagram|tiktok|x|twitter|linkedin|threads|msn)\b", re.I)

# Clasificación por tema: patrones con peso; gana el tema con mayor puntaje
TEMAS = {
    "ingenieria_sistemas": [
        (r"ingenier[ií]a de (sistemas|software)|ingenier[ií]a inform[aá]tica|ingenieros? de software", 3),
        (r"programaci[oó]n|programador|desarrollador|desarrollo de software|\bsoftware\b|c[oó]digo abierto|open source", 2),
        (r"ciberseguridad|ciencia de datos|base de datos|big data|algoritmo|devops|\bnube\b|cloud|github|python|"
         r"javascript|\bapi\b|machine learning|aprendizaje autom[aá]tico|linux|hackat", 2),
    ],
    "tecnologia": [
        (r"tecnolog|inteligencia artificial|\bia\b|chatgpt|openai|gemini|copilot|robot|\bchip|semiconductor", 2),
        (r"smartphone|celular|iphone|android|apple|google|microsoft|\bmeta\b|samsung|\b5g\b|internet|wifi|"
         r"digital|startup|ciber|hacker|criptomoneda|videojuego|\bapp\b|aplicaci[oó]n", 1),
    ],
    "educacion": [
        (r"educaci[oó]n|educativ|mineducaci|icetex|saber 11|saber pro|acreditaci", 3),
        (r"universidad|universitari|colegio|escuela|docente|maestr[oa]s?\b|estudiante|bachiller|pregrado|"
         r"posgrado|matr[ií]cula|beca|aprendizaje|alfabetizaci|\bsena\b|rector|icfes|\buptc\b|\bunal\b", 1),
    ],
}
TEMA_HINT_BONUS = 2   # la consulta / el feed de origen suma a su tema
BOGOTA = timezone(timedelta(hours=-5))
ID_EXTERNO = 10**12   # noticia_id >= ID_EXTERNO → id derivado de la URL (no es un post de WordPress)


def clasificar(texto: str) -> str:
    t = texto.lower()
    for tipo, patron in REGLAS_TIPO:
        if re.search(patron, t):
            return tipo
    return "general"


def puntaje_temas(texto: str) -> dict[str, int]:
    t = texto.lower()
    return {tema: sum(w for p, w in reglas if re.search(p, t)) for tema, reglas in TEMAS.items()}


def clasificar_tema(titulo: str, resumen: str, hint: str | None = None, institucional: bool = False) -> str:
    """Tema por reglas de palabras clave + consulta de origen.

    UNAB → 'institucional', salvo que el TITULAR sea claramente de tecnología/ingeniería
    (puntaje ≥ 4) o de educación general (≥ 5, porque casi toda noticia UNAB habla de estudiantes).
    """
    if institucional:
        pt = puntaje_temas(titulo)
        umbral = {"ingenieria_sistemas": 4, "tecnologia": 4, "educacion": 5}
        tema, score = max(pt.items(), key=lambda kv: kv[1])
        return tema if score >= umbral[tema] else "institucional"
    pt = puntaje_temas(f"{titulo} {titulo} {resumen}")
    if hint in pt:
        pt[hint] += TEMA_HINT_BONUS
    tema, score = max(pt.items(), key=lambda kv: (kv[1], kv[0] == hint))
    return tema if score > 0 else (hint or "tecnologia")


def id_estable(url: str) -> int:
    """noticia_id para fuentes sin id propio: hash estable de la URL, fuera del rango de WordPress."""
    return ID_EXTERNO + int(hashlib.sha1(url.encode("utf-8")).hexdigest()[:10], 16)


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
                        relevancia=relevancia(titulo, resumen, fecha),
                        tema=clasificar_tema(titulo, resumen, institucional=True), fuente_nombre="UNAB"))
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
        out.append(dict(noticia_id=id_estable(a["href"]), titulo=titulo, url=a["href"], fecha_pub=fecha,
                        categoria="Estudiantes (HTML)", tipo=clasificar(titulo), resumen=resumen, contenido=resumen,
                        relevancia=relevancia(titulo, resumen, fecha),
                        tema=clasificar_tema(titulo, resumen, institucional=True), fuente_nombre="UNAB"))
    return out


# ---------------------------------------------------------------------------
# RSS / Atom
# ---------------------------------------------------------------------------
ATOM = "{http://www.w3.org/2005/Atom}"


def _fecha_feed(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)                                   # RFC 822 (RSS 2.0)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))       # ISO 8601 (Atom, El Tiempo)
        except ValueError:
            return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _txt(el: ET.Element, *tags: str) -> str | None:
    for t in tags:
        v = el.find(t)
        if v is not None:
            val = (v.text or v.get("href") or "").strip()
            if val:
                return val
    return None


def desde_rss(dias: int) -> list[dict]:
    """Noticias de FUENTES_RSS (RSS 2.0 o Atom) publicadas en los últimos `dias` días."""
    ahora = datetime.now(timezone.utc)
    limite, futuro = ahora - timedelta(days=dias), ahora + timedelta(hours=6)
    out = []
    for nombre, url, hint, agregador in FUENTES_RSS:
        url = url.replace("{d}", str(max(1, dias)))
        try:
            r = requests.get(url, headers={**HEADERS, "Accept": "application/rss+xml, application/xml"}, timeout=25)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as exc:  # una fuente caída no detiene a las demás
            print(f"  ! {nombre}: {type(exc).__name__} {str(exc)[:80]}")
            continue
        items = root.findall(".//item") or root.findall(f".//{ATOM}entry")
        n_ok = 0
        for it in items:
            titulo = limpiar(_txt(it, "title", f"{ATOM}title") or "")
            link = _txt(it, "link", f"{ATOM}link")
            fecha = _fecha_feed(_txt(it, "pubDate", f"{ATOM}published", f"{ATOM}updated",
                                     "{http://purl.org/dc/elements/1.1/}date"))
            if not titulo or not link or not fecha or not (limite <= fecha <= futuro):
                continue
            medio = nombre
            src = it.find("source")
            if agregador and src is not None and (src.text or "").strip():
                medio = src.text.strip()
                if titulo.endswith(f" - {medio}"):
                    titulo = titulo[: -len(medio) - 3].strip()
                if NO_MEDIOS.search(medio):
                    continue  # redes sociales y videos: no son medios con fuente verificable
            resumen = limpiar(_txt(it, "description", f"{ATOM}summary", f"{ATOM}content") or "")
            resumen = re.sub(r"\s*(La entrada .*? se publicó primero en|The post .*? appeared first on|Leer más|"
                             r"Seguir leyendo|\[…\]|\[\.\.\.\]).*$", "", resumen)
            if agregador or resumen.lower().startswith(titulo.lower()[:40]):
                resumen = ""  # en Google News la descripción solo repite titular + medio
            resumen = resumen[:600]
            if COMERCIAL.search(titulo):
                continue
            if not agregador and max(puntaje_temas(f"{titulo} {resumen}").values()) == 0:
                continue  # feeds generalistas: exige al menos una palabra clave de los temas
            tema = clasificar_tema(titulo, resumen, hint)
            rel = relevancia(titulo, resumen, fecha) + {"ingenieria_sistemas": 1.5, "educacion": 1.0}.get(tema, 0.5)
            out.append(dict(noticia_id=id_estable(link), titulo=titulo, url=link, fecha_pub=fecha,
                            categoria=f"RSS: {nombre}", tipo=clasificar(f"{titulo} {resumen}"), resumen=resumen,
                            contenido=resumen or titulo, relevancia=round(rel, 2), tema=tema, fuente_nombre=medio))
            n_ok += 1
            if n_ok >= MAX_POR_FUENTE:
                break
        print(f"  · {nombre:<24} {n_ok:>3} recientes  (tema sugerido: {hint})")
    return out


def deduplicar(noticias: list[dict]) -> list[dict]:
    """Una noticia por URL y por titular normalizado (Google News repite notas entre consultas)."""
    urls, titulos, out = set(), set(), []
    for n in noticias:
        clave = re.sub(r"\W+", " ", n["titulo"].lower()).strip()[:90]
        if n["url"] in urls or clave in titulos:
            continue
        urls.add(n["url"])
        titulos.add(clave)
        out.append(n)
    return out


def guardar(noticias: list[dict], embed: bool) -> tuple[int, int]:
    import psycopg

    nuevas = 0
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, extensions")
        cur.execute("""SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbot'
                       AND table_name = 'noticia' AND column_name = 'tema'""")
        con_tema = cur.fetchone() is not None  # compatibilidad si aún no se aplicó 06_noticias_temas.sql
        cols = "noticia_id, titulo, url, fecha_pub, categoria, tipo, resumen, contenido, relevancia"
        vals = ("%(noticia_id)s, %(titulo)s, %(url)s, %(fecha_pub)s, %(categoria)s, %(tipo)s, %(resumen)s, "
                "%(contenido)s, %(relevancia)s")
        upd = "relevancia = EXCLUDED.relevancia, scrapeado_en = now()"
        if con_tema:
            cols += ", tema, fuente_nombre"
            vals += ", %(tema)s, %(fuente_nombre)s"
            upd += ", tema = EXCLUDED.tema, fuente_nombre = EXCLUDED.fuente_nombre"
        for n in noticias:
            # UNAB: conflicto por id del CMS; fuentes externas: deduplicación por URL
            conflicto = "url" if n["noticia_id"] >= ID_EXTERNO else "noticia_id"
            cur.execute(f"""INSERT INTO chatbot.noticia ({cols}) VALUES ({vals})
                            ON CONFLICT ({conflicto}) DO UPDATE SET {upd}
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

    fuente = n.get("fuente_nombre") or "UNAB"
    texto = f"Noticia {fuente} ({n['fecha_pub']:%Y-%m-%d}): {n['titulo']}\n{(n['contenido'] or '')[:1800]}"
    global _GENAI
    if _GENAI is None:
        _GENAI = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    v = _GENAI.models.embed_content(
        model=os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001"), contents=texto,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")).embeddings[0].values
    md = {"titulo": n["titulo"], "url": n["url"], "fuente": "Noticias UNAB" if fuente == "UNAB" else fuente,
          "origen": "noticia", "tema": n.get("tema"), "fecha": n["fecha_pub"].date().isoformat()}
    cur.execute("INSERT INTO chatbot.rag_documentos (text, metadata, embedding) VALUES (%s, %s::jsonb, %s::vector)",
                (texto, json.dumps(md, ensure_ascii=False), "[" + ",".join(map(str, v)) + "]"))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=3, help="solo noticias de los últimos N días (fuentes RSS externas)")
    ap.add_argument("--dias-unab", type=int, default=180, help="ventana hacia atrás para unab.edu.co (como antes)")
    ap.add_argument("--fuentes", choices=["todas", "unab", "rss"], default="todas")
    ap.add_argument("--embed", action="store_true", help="vectorizar noticias nuevas en el RAG")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    data: list[dict] = []
    if a.fuentes in ("todas", "unab"):
        try:
            unab = desde_api(a.dias_unab)
            origen = "API WordPress"
        except Exception as exc:
            print("API no disponible, usando fallback HTML:", exc)
            unab, origen = desde_html(), "HTML"
        print(f"UNAB: {len(unab)} noticias vía {origen} (últimos {a.dias_unab} días)")
        data += unab
    if a.fuentes in ("todas", "rss"):
        print(f"RSS externos (últimos {a.dias} días):")
        data += desde_rss(a.dias)
    data = deduplicar(data)
    data.sort(key=lambda n: -n["relevancia"])
    hoy = datetime.now(BOGOTA).date()
    print(f"{len(data)} noticias tras deduplicar · por tema: {dict(Counter(n['tema'] for n in data))}")
    print(f"  de hoy ({hoy}, hora Colombia): {sum(n['fecha_pub'].astimezone(BOGOTA).date() == hoy for n in data)}"
          f" · más reciente: {max((n['fecha_pub'] for n in data), default=None)}")
    for n in sorted(data, key=lambda n: n["fecha_pub"], reverse=True)[:12]:
        print(f"  [{n['tema']:<19}] {n['fecha_pub'].astimezone(BOGOTA):%Y-%m-%d %H:%M}  "
              f"{n['fuente_nombre'][:22]:<22} {n['titulo'][:70]}")
    if not a.dry_run:
        total, nuevas = guardar(data, a.embed)
        print(f"Guardadas {total} ({nuevas} nuevas)")
