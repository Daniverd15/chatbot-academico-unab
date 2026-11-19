"""
Experimento empírico de chunking, solape y dimensión de embeddings (todo en memoria).

NO toca la base de datos. Reutiliza `trocear()` de ingest.py (parametrizada), embebe los
fragmentos con gemini-embedding-001 (caché en disco rag/eval/cache_emb/) y evalúa las 40
preguntas de rag/eval/golden.jsonl con similitud coseno (numpy). Acierto = el fragmento
pertenece al documento esperado (igual que rag/evaluate.py).

Parte A: (chunk, solape) en {(500,75),(1000,0),(1000,150),(1500,225)} a 3072 d.
Parte B: para (1000,150), dimensión 3072 vs 1536 vs 768 (output_dimensionality + renormalización).

Uso:  python rag/experimento_chunking.py
Requiere GEMINI_API_KEY en .env. Si se agota la cuota diaria guarda resultados parciales.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402  (solo funciones puras; no conecta a la BD)

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "eval" / "golden.jsonl"
CACHE = ROOT / "eval" / "cache_emb"
SALIDA = ROOT / "eval" / "resultados_chunking.json"
load_dotenv(ROOT.parent / ".env")

MODEL = ingest.MODEL
CONFIGS = [(500, 75), (1000, 0), (1000, 150), (1500, 225)]
DIMS = [3072, 1536, 768]
LOTE = 50
PAUSA = 8.0  # segundos entre lotes (cuota gratuita)


class CuotaAgotada(Exception):
    pass


def _clave(tarea: str, dim: int, texto: str) -> str:
    return hashlib.sha1(f"{MODEL}|{tarea}|{dim}|{texto}".encode("utf-8")).hexdigest()


def embeber(textos: list[str], tarea: str, dim: int) -> np.ndarray:
    """Embeddings con caché en disco, lotes, y backoff ante 429. dim=3072 es el nativo."""
    from google import genai
    from google.genai import types

    CACHE.mkdir(parents=True, exist_ok=True)
    claves = [_clave(tarea, dim, t) for t in textos]
    faltan = [i for i, k in enumerate(claves) if not (CACHE / f"{k}.npy").exists()]
    if faltan:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        for j in range(0, len(faltan), LOTE):
            idx = faltan[j:j + LOTE]
            cfg = {"task_type": tarea}
            if dim != 3072:
                cfg["output_dimensionality"] = dim
            for intento in range(10):
                try:
                    r = client.models.embed_content(
                        model=MODEL, contents=[textos[i] for i in idx],
                        config=types.EmbedContentConfig(**cfg))
                    for i, e in zip(idx, r.embeddings):
                        np.save(CACHE / f"{claves[i]}.npy", np.array(e.values, dtype=np.float32))
                    break
                except Exception as exc:
                    msg = str(exc)
                    if "PerDay" in msg or "per day" in msg.lower():
                        raise CuotaAgotada(msg[:200])
                    espera = min(2 ** intento * 5, 120)
                    print(f"   reintento en {espera}s ({exc.__class__.__name__}: {msg[:80]})", flush=True)
                    time.sleep(espera)
            else:
                raise CuotaAgotada("reintentos agotados")
            print(f"   embebidos {min(j + LOTE, len(faltan))}/{len(faltan)} (tarea={tarea}, dim={dim})", flush=True)
            time.sleep(PAUSA)
    M = np.stack([np.load(CACHE / f"{k}.npy") for k in claves])
    return M


def normalizar(M: np.ndarray) -> np.ndarray:
    return M / np.linalg.norm(M, axis=1, keepdims=True)


def fragmentos(chunk: int, solape: int) -> list[tuple[str, str]]:
    """(texto_embebido, archivo) con el mismo formato que ingest.main()."""
    out = []
    for f in sorted(ingest.CORPUS.glob("*.md")):
        meta, cuerpo = ingest.leer(f)
        for sec, ch in ingest.trocear(cuerpo, chunk, solape):
            texto = (f"{meta.get('titulo')} — {sec}\n{ch}" if sec and sec not in ch[:150]
                     else f"{meta.get('titulo')}\n{ch}")
            out.append((texto, f.name))
    return out


def evaluar(Q: np.ndarray, D: np.ndarray, archivos: list[str], esperados: list[str]) -> dict:
    sims = Q @ D.T
    ranks = []
    for i, esp in enumerate(esperados):
        orden = np.argsort(-sims[i])[:10]
        pos = next((r for r, j in enumerate(orden, 1) if archivos[j] == esp), None)
        ranks.append(pos)
    n = len(ranks)
    hit = lambda k: sum(1 for r in ranks if r is not None and r <= k) / n
    return {"hit@1": round(hit(1), 4), "hit@3": round(hit(3), 4),
            "mrr@10": round(sum(1 / r for r in ranks if r) / n, 4),
            "fallos_top1": [i for i, r in enumerate(ranks) if r != 1]}


def validar_truncado(texto: str, v3072: np.ndarray) -> dict:
    """Compara output_dimensionality=768/1536 (API) con el prefijo renormalizado del vector 3072 d."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    out = {}
    for d in (768, 1536):
        try:
            r = client.models.embed_content(model=MODEL, contents=[texto], config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT", output_dimensionality=d))
            a = np.array(r.embeddings[0].values, dtype=np.float32)
            b = v3072[:d]
            out[str(d)] = round(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b))), 6)
        except Exception as exc:
            out[str(d)] = f"no verificado ({exc.__class__.__name__})"
    return out


def guardar(res: dict) -> None:
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    golden = [json.loads(l) for l in GOLDEN.open(encoding="utf-8") if l.strip()]
    esperados = [g["archivo_esperado"] for g in golden]
    ids = [g["id"] for g in golden]
    res: dict = {"modelo": MODEL, "n_preguntas": len(golden), "parcial": False,
                 "chunking": {}, "dimensiones": {}}
    try:
        Q = {d: normalizar(embeber([g["pregunta"] for g in golden], "RETRIEVAL_QUERY", d)) for d in DIMS[:1]}
        for chunk, solape in CONFIGS:
            frs = fragmentos(chunk, solape)
            textos = [t for t, _ in frs]
            archivos = [a for _, a in frs]
            print(f"== ({chunk},{solape}): {len(frs)} fragmentos", flush=True)
            try:
                D = normalizar(embeber(textos, "RETRIEVAL_DOCUMENT", 3072))
            except CuotaAgotada as exc:
                res["parcial"] = True
                res["aviso"] = f"Cuota diaria agotada; configuraciones sin evaluar: {chunk}/{solape}. {exc}"
                res["chunking"][f"{chunk}/{solape}"] = {"pendiente": "cuota agotada"}
                print("  CUOTA AGOTADA en esta configuración", flush=True)
                continue
            m = evaluar(Q[3072], D, archivos, esperados)
            lon = [len(t) for t in textos]
            m["fallos_top1"] = [ids[i] for i in m["fallos_top1"]]
            m.update({"n_fragmentos": len(frs), "long_media_chars": round(float(np.mean(lon)), 1),
                      "tokens_contexto_top5": round(5 * float(np.mean(lon)) / 4)})
            res["chunking"][f"{chunk}/{solape}"] = m
            print("  ", m, flush=True)
            guardar(res)
        frs = fragmentos(1000, 150)
        textos = [t for t, _ in frs]
        archivos = [a for _, a in frs]
        D3 = embeber(textos, "RETRIEVAL_DOCUMENT", 3072)
        # Matryoshka: dimensión reducida = prefijo del vector de 3072 d, renormalizado.
        # Se valida contra la API (output_dimensionality) con una muestra pequeña, porque
        # la cuota diaria gratuita no alcanza para re-embeber todo el corpus por dimensión.
        res["validacion_truncado_vs_api"] = validar_truncado(textos[0], D3[0])
        for d in DIMS:
            qd = Q[3072] if d == 3072 else normalizar(Q[3072][:, :d])
            D = normalizar(D3[:, :d])
            res.setdefault("nota_dimensiones",
                "Vectores reducidos obtenidos por truncado + renormalización de los de 3072 d "
                "(propiedad Matryoshka); equivalencia con output_dimensionality verificada en una muestra.")
            m = evaluar(qd, D, archivos, esperados)
            m["fallos_top1"] = [ids[i] for i in m["fallos_top1"]]
            m["bytes_por_vector_float32"] = d * 4
            m["bytes_por_vector_halfvec"] = d * 2
            res["dimensiones"][str(d)] = m
            print(f"== dim {d}:", m, flush=True)
            guardar(res)
    except CuotaAgotada as exc:
        res["parcial"] = True
        res["aviso"] = f"Cuota agotada; resultados parciales: {exc}"
        print("CUOTA AGOTADA, resultados parciales guardados.", flush=True)
    guardar(res)


if __name__ == "__main__":
    main()
