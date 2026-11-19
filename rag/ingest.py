"""
Ingesta del RAG (alternativa en Python al workflow n8n "00 - Ingesta RAG").

corpus/md/*.md ──► chunking jerárquico (secciones → párrafos, ~1000 caracteres,
solape 150) ──► embeddings Gemini (gemini-embedding-001, RETRIEVAL_DOCUMENT,
3072 d) ──► chatbot.rag_documentos (pgvector)

Uso:
    python rag/ingest.py              # reemplaza todo el contenido
    python rag/ingest.py --dry-run    # solo muestra estadísticas de chunking
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus" / "md"
load_dotenv(ROOT.parent / ".env")

CHUNK = 1000
SOLAPE = 150
MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")


def leer(path: Path) -> tuple[dict, str]:
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.S)
    return (json.loads(m.group(1)), m.group(2)) if m else ({"titulo": path.stem}, txt)


def trocear(texto: str, CHUNK: int = CHUNK, SOLAPE: int = SOLAPE) -> list[tuple[str, str]]:
    """Devuelve (seccion, chunk). Respeta encabezados '## ' y párrafos/artículos.
    CHUNK y SOLAPE son parametrizables (defaults = valores de producción; usado por
    rag/experimento_chunking.py)."""
    cola = (lambda t: t[-SOLAPE:]) if SOLAPE > 0 else (lambda t: "")
    out: list[tuple[str, str]] = []
    secciones = re.split(r"\n(?=## )", texto)
    for sec in secciones:
        titulo = sec.split("\n", 1)[0].lstrip("# ").strip()[:120]
        parrafos = [p.strip() for p in re.split(r"\n\s*\n", sec) if p.strip()]
        actual = ""
        for p in parrafos:
            while len(p) > CHUNK * 1.5:  # párrafo gigante → cortar por oraciones
                corte = p.rfind(". ", 0, CHUNK) + 1 or CHUNK
                parrafos_extra, p = p[:corte], p[corte:].strip()
                if actual:
                    out.append((titulo, actual))
                    actual = cola(actual)
                out.append((titulo, (actual + " " + parrafos_extra).strip()))
                actual = cola(parrafos_extra)
            if len(actual) + len(p) + 2 <= CHUNK:
                actual = (actual + "\n\n" + p).strip()
            else:
                if actual:
                    out.append((titulo, actual))
                actual = (cola(actual) + "\n\n" + p).strip() if actual else p
        if actual.strip():
            out.append((titulo, actual))
    return [(t, c) for t, c in out if len(c) > 80]


def embed_lote(client, textos: list[str]) -> list[list[float]]:
    from google.genai import types

    for intento in range(6):
        try:
            r = client.models.embed_content(
                model=MODEL, contents=textos,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return [e.values for e in r.embeddings]
        except Exception as exc:  # cuota gratuita: reintento exponencial
            espera = 2 ** intento * 5
            print(f"   reintento en {espera}s ({exc.__class__.__name__}: {str(exc)[:80]})")
            time.sleep(espera)
    raise RuntimeError("No fue posible generar embeddings")


def main(dry: bool) -> None:
    docs = []
    for f in sorted(CORPUS.glob("*.md")):
        meta, cuerpo = leer(f)
        for i, (sec, ch) in enumerate(trocear(cuerpo)):
            texto = f"{meta.get('titulo')} — {sec}\n{ch}" if sec and sec not in ch[:150] else f"{meta.get('titulo')}\n{ch}"
            docs.append((texto, {**meta, "seccion": sec, "chunk": i, "archivo": f.name}))
    largos = [len(d[0]) for d in docs]
    print(f"{len(docs)} fragmentos de {len(list(CORPUS.glob('*.md')))} documentos · "
          f"long. media {sum(largos) / len(largos):.0f} · máx {max(largos)}")
    if dry:
        return

    import psycopg
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SET search_path = public, extensions")
        cur.execute("DELETE FROM chatbot.rag_documentos WHERE metadata->>'origen' IS DISTINCT FROM 'noticia'")
        for i in range(0, len(docs), 40):
            lote = docs[i:i + 40]
            vecs = embed_lote(client, [d[0] for d in lote])
            cur.executemany(
                "INSERT INTO chatbot.rag_documentos (text, metadata, embedding) VALUES (%s, %s::jsonb, %s::vector)",
                [(d[0], json.dumps(d[1], ensure_ascii=False), "[" + ",".join(map(str, v)) + "]")
                 for d, v in zip(lote, vecs)],
            )
            conn.commit()
            print(f"  {min(i + 40, len(docs))}/{len(docs)} insertados (dim={len(vecs[0])})")
            time.sleep(1)
    print("Ingesta completa.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    main(ap.parse_args().dry_run)
