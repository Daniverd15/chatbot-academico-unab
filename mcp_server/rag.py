"""
Recuperación híbrida para el RAG institucional.

    pregunta ──► embedding (gemini-embedding-001, 3072d) ──► pgvector (coseno, HNSW halfvec)
            └──► full-text search en español (tsvector)  ──┘
                              Reciprocal Rank Fusion (k=60) ──► top-k fragmentos con fuente
"""
from __future__ import annotations

import os
from functools import lru_cache

from db import query

EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")


@lru_cache(maxsize=1)
def _client():
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


@lru_cache(maxsize=256)
def embed(texto: str) -> tuple[float, ...]:
    from google.genai import types

    r = _client().models.embed_content(
        model=EMBED_MODEL,
        contents=texto,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return tuple(r.embeddings[0].values)


def _vec_literal(v: tuple[float, ...]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def buscar(pregunta: str, k: int = 5, fuente: str | None = None) -> list[dict]:
    filtro = '{"fuente": "%s"}' % fuente.replace('"', "") if fuente else "{}"
    resultados: dict[str, dict] = {}
    scores: dict[str, float] = {}

    try:
        vec = _vec_literal(embed(pregunta))
        sem = query(
            "SELECT id::text, text, metadata, similitud FROM chatbot.match_documentos(%s::vector, %s, %s::jsonb)",
            (vec, k * 2, filtro),
        )
    except Exception as exc:  # si Gemini falla seguimos con búsqueda léxica
        sem = []
        print(f"[rag] embedding no disponible: {exc}")

    lex = query("SELECT id::text, text, metadata, rank FROM chatbot.buscar_texto(%s, %s)", (pregunta, k * 2))

    # RRF ponderado: semántico peso 1.0; léxico RRF_PESO_LEXICO (ver docs/evaluacion_rag.md)
    peso_lex = float(os.environ.get("RRF_PESO_LEXICO", "0.0"))
    for lista, peso in ((sem, 1.0), (lex, peso_lex)):
        for pos, row in enumerate(lista):
            resultados.setdefault(row["id"], row)
            scores[row["id"]] = scores.get(row["id"], 0.0) + peso / (60 + pos + 1)

    top = sorted(scores, key=scores.get, reverse=True)[:k]
    out = []
    for rid in top:
        r = resultados[rid]
        md = r.get("metadata") or {}
        out.append(
            {
                "fragmento": r["text"],
                "titulo": md.get("titulo") or md.get("title"),
                "fuente": md.get("url") or md.get("source") or md.get("fuente"),
                "similitud": round(r["similitud"], 3) if "similitud" in r else None,
                "score_rrf": round(scores[rid], 4),
            }
        )
    return out
