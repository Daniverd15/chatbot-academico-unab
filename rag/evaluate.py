"""
Evaluación de la calidad de recuperación del RAG (retrieval) sobre un conjunto dorado.

Para cada pregunta de rag/eval/golden.jsonl se calcula la posición (1-based) del primer
fragmento que pertenece al documento esperado, con tres métodos:

  semantico : chatbot.match_documentos (embedding Gemini RETRIEVAL_QUERY + coseno halfvec)
  lexico    : chatbot.buscar_texto     (tsvector 'spanish' + websearch_to_tsquery)
  hibrido   : Reciprocal Rank Fusion (k=60) de ambos, igual que mcp_server/rag.py

Métricas: hit@1, hit@3, hit@5 y MRR@10 (global y por categoría).
Resultados: tabla en consola + rag/eval/resultados.json

Uso:
    python rag/evaluate.py [--k 5]

Requiere DATABASE_URL y GEMINI_API_KEY en el entorno (se cargan desde .env).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus" / "md"
GOLDEN = ROOT / "eval" / "golden.jsonl"
SALIDA = ROOT / "eval" / "resultados.json"
load_dotenv(ROOT.parent / ".env")

EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
K_MAX = 10          # profundidad de recuperación evaluada
RRF_K = 60          # constante de Reciprocal Rank Fusion (igual que mcp_server/rag.py)
PESO_LEXICO_DEFECTO = float(os.environ.get("RRF_PESO_LEXICO", "0.0"))  # peso del canal léxico (semántico = 1.0)
PESOS_BARRIDO = (0.0, 0.25, 0.5, 0.75, 1.0)
METODOS = ("semantico", "lexico", "hibrido")


# ------------------------------------------------------------------ utilidades
def cargar_golden() -> list[dict]:
    with GOLDEN.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def url_de(archivo: str) -> str | None:
    """URL declarada en el front-matter del documento (para emparejar filas del scraper)."""
    txt = (CORPUS / archivo).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
    return json.loads(m.group(1)).get("url") if m else None


def vec_literal(v) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def embeber(textos: list[str]) -> list[list[float]]:
    """Embeddings RETRIEVAL_QUERY en lotes, con reintento exponencial ante 429 (cuota gratuita)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    out: list[list[float]] = []
    for i in range(0, len(textos), 50):
        lote = textos[i:i + 50]
        for intento in range(8):
            try:
                r = client.models.embed_content(
                    model=EMBED_MODEL, contents=lote,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
                )
                out.extend(e.values for e in r.embeddings)
                break
            except Exception as exc:
                espera = min(2 ** intento * 5, 120)
                print(f"  embedding: reintento en {espera}s ({exc.__class__.__name__}: {str(exc)[:80]})")
                time.sleep(espera)
        else:
            raise RuntimeError("No fue posible generar los embeddings de las preguntas")
    return out


def es_acierto(md: dict, esperado: str, url_esperada: str | None) -> bool:
    if md.get("archivo") == esperado:
        return True
    # filas insertadas por el scraper de noticias: sin 'archivo', con origen='noticia'
    return bool(md.get("origen") == "noticia" and not md.get("archivo")
                and url_esperada and md.get("url") == url_esperada)


def posicion(filas: list[dict], esperado: str, url_esperada: str | None) -> int | None:
    for i, f in enumerate(filas[:K_MAX], 1):
        if es_acierto(f["metadata"] or {}, esperado, url_esperada):
            return i
    return None


def rrf(sem: list[dict], lex: list[dict], w_lex: float = 1.0) -> list[dict]:
    """Misma fusión que mcp_server/rag.py: sum(peso/(60 + pos + 1)), pos 0-based.
    Peso 1.0 para la lista semántica y `w_lex` para la léxica."""
    filas: dict[str, dict] = {}
    scores: dict[str, float] = {}
    for lista, peso in ((sem, 1.0), (lex, w_lex)):
        for pos, row in enumerate(lista):
            filas.setdefault(row["id"], row)
            scores[row["id"]] = scores.get(row["id"], 0.0) + peso / (RRF_K + pos + 1)
    orden = sorted(scores, key=scores.get, reverse=True)
    return [filas[i] for i in orden]


def metricas(ranks: list[int | None]) -> dict:
    n = len(ranks) or 1
    hit = lambda k: sum(1 for r in ranks if r is not None and r <= k) / n
    mrr = sum(1.0 / r for r in ranks if r is not None) / n
    return {"hit@1": round(hit(1), 4), "hit@3": round(hit(3), 4),
            "hit@5": round(hit(5), 4), "mrr": round(mrr, 4)}


# ------------------------------------------------------------------ principal
def main(k: int, w_lex: float, barrido: bool) -> None:
    import psycopg
    from psycopg.rows import dict_row

    golden = cargar_golden()
    urls = {g["archivo_esperado"]: url_de(g["archivo_esperado"]) for g in golden}
    print(f"{len(golden)} preguntas · recuperación a k={K_MAX} · embeddings con {EMBED_MODEL}")

    vecs = embeber([g["pregunta"] for g in golden])

    por_pregunta: list[dict] = []
    listas: list[tuple[dict, list[dict], list[dict]]] = []  # (pregunta, sem, lex) reutilizadas en el barrido
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True,
                         prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, extensions")
        for g, v in zip(golden, vecs):
            # listas de 2*K_MAX como en mcp_server/rag.py (k*2); los métodos simples se miden en el top K_MAX
            cur.execute(
                "SELECT id::text AS id, text, metadata, similitud "
                "FROM chatbot.match_documentos(%s::vector, %s, %s::jsonb)",
                (vec_literal(v), K_MAX * 2, "{}"),
            )
            sem = cur.fetchall()
            cur.execute(
                "SELECT id::text AS id, text, metadata, rank FROM chatbot.buscar_texto(%s, %s)",
                (g["pregunta"], K_MAX * 2),
            )
            lex = cur.fetchall()
            hib = rrf(sem, lex, w_lex)
            listas.append((g, sem, lex))
            esp, url = g["archivo_esperado"], urls[g["archivo_esperado"]]
            por_pregunta.append({
                "id": g["id"], "pregunta": g["pregunta"], "categoria": g["categoria"], "esperado": esp,
                "rank_semantico": posicion(sem, esp, url),
                "rank_lexico": posicion(lex, esp, url),
                "rank_hibrido": posicion(hib, esp, url),
            })

    def agregar(filas: list[dict]) -> dict:
        return {m: metricas([f[f"rank_{m}"] for f in filas]) for m in METODOS}

    categorias = sorted({p["categoria"] for p in por_pregunta})
    resultado = {
        "fecha": date.today().isoformat(),
        "n_preguntas": len(por_pregunta),
        "k": K_MAX,
        "peso_lexico": w_lex,
        "metodos": agregar(por_pregunta),
        "por_categoria": {c: agregar([p for p in por_pregunta if p["categoria"] == c]) for c in categorias},
        "por_pregunta": por_pregunta,
    }
    if barrido:
        barr = {}
        for w in PESOS_BARRIDO:
            ranks = [posicion(rrf(sem, lex, w), g["archivo_esperado"], urls[g["archivo_esperado"]])
                     for g, sem, lex in listas]
            barr[str(w)] = metricas(ranks)
        resultado["barrido_peso_lexico"] = barr
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- tabla en consola
    def tabla(titulo: str, datos: dict, n: int) -> None:
        print(f"\n{titulo} (n={n})")
        print(f"{'método':<11}{'hit@1':>8}{'hit@3':>8}{'hit@5':>8}{'MRR@10':>9}")
        for m in METODOS:
            d = datos[m]
            print(f"{m:<11}{d['hit@1']:>8.3f}{d['hit@3']:>8.3f}{d['hit@5']:>8.3f}{d['mrr']:>9.3f}")

    tabla("GLOBAL", resultado["metodos"], len(por_pregunta))
    for c in categorias:
        n = sum(1 for p in por_pregunta if p["categoria"] == c)
        tabla(f"Categoría: {c}", resultado["por_categoria"][c], n)

    print(f"\nPeso léxico usado para 'hibrido': {w_lex}")
    if barrido:
        print("\nBARRIDO del peso léxico en RRF (semántico = 1.0)")
        print(f"{'w_lex':<8}{'hit@1':>8}{'hit@3':>8}{'hit@5':>8}{'MRR@10':>9}")
        for w, d in resultado["barrido_peso_lexico"].items():
            print(f"{w:<8}{d['hit@1']:>8.3f}{d['hit@3']:>8.3f}{d['hit@5']:>8.3f}{d['mrr']:>9.3f}")

    kk = min(k, K_MAX)
    print(f"\nAciertos en top-{kk}: " + " · ".join(
        f"{m} {sum(1 for p in por_pregunta if p[f'rank_{m}'] is not None and p[f'rank_{m}'] <= kk)}/{len(por_pregunta)}"
        for m in METODOS))
    print(f"Resultados escritos en {SALIDA.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Evaluación de recuperación del RAG")
    ap.add_argument("--k", type=int, default=5, help="k del resumen de aciertos en consola (máx. 10)")
    ap.add_argument("--w-lex", type=float, default=PESO_LEXICO_DEFECTO,
                    help="peso del canal léxico en RRF (semántico = 1.0); defecto: env RRF_PESO_LEXICO o 0.0 (ver docs/evaluacion_rag.md)")
    ap.add_argument("--barrido", action="store_true", help="evalúa el híbrido con w_lex en 0, .25, .5, .75, 1")
    a = ap.parse_args()
    main(a.k, a.w_lex, a.barrido)
