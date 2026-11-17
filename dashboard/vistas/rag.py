"""Página 6 · Calidad del RAG (evaluación de recuperación + corpus)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import json  # noqa: E402
import os  # noqa: E402

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402
from lib.db import DASHBOARD_DIR, REPO_ROOT  # noqa: E402

ui.encabezado(
    "Calidad del RAG",
    "Qué tan bien recupera el asistente los documentos institucionales correctos. Se comparan tres métodos "
    "sobre un conjunto de preguntas con documento esperado: búsqueda semántica (embeddings Gemini + pgvector), "
    "léxica (texto completo) e híbrida. Hit@k = la fuente esperada aparece entre los k primeros; "
    "MRR = promedio de 1/posición.",
)

METODOS = {"semantico": ("Semántico", ui.MORADO), "lexico": ("Léxico", ui.NARANJA), "hibrido": ("Híbrido", ui.VERDE)}
METRICAS = ["hit@1", "hit@3", "hit@5", "mrr"]


def _ruta_eval() -> Path | None:
    cands = []
    if os.environ.get("DASH_RAG_EVAL"):
        cands.append(Path(os.environ["DASH_RAG_EVAL"]))
    cands += [REPO_ROOT / "rag" / "eval" / "resultados.json", Path("/app/rag_eval/resultados.json"),
              DASHBOARD_DIR / "rag_eval" / "resultados.json"]
    return next((p for p in cands if p.is_file()), None)


@st.cache_data(ttl=300, show_spinner=False)
def _leer(ruta: str, mtime: float) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


ruta = _ruta_eval()
ev = None
if ruta:
    try:
        ev = _leer(str(ruta), ruta.stat().st_mtime)
    except (OSError, ValueError) as e:
        st.warning(f"No se pudo leer {ruta.name}: {type(e).__name__}.")

if ev and isinstance(ev.get("metodos"), dict):
    met = ev["metodos"]
    presentes = [m for m in METODOS if m in met] + [m for m in met if m not in METODOS]
    mejor = max(presentes, key=lambda m: met[m].get("mrr", 0))
    h = met.get("hibrido", {})
    ui.kpis([
        ui.KPI("Preguntas evaluadas", ui.num(ev.get("n_preguntas")), f"evaluación del {ev.get('fecha', '—')} · k = {ev.get('k', '—')}", ui.AZUL),
        ui.KPI("Hit@1 híbrido", ui.pct(100 * h["hit@1"]) if "hit@1" in h else "—", "fuente correcta en primer lugar", ui.VERDE),
        ui.KPI("Hit@5 híbrido", ui.pct(100 * h["hit@5"]) if "hit@5" in h else "—", "fuente correcta en el top 5", ui.MORADO),
        ui.KPI("Mejor MRR", ui.num(met[mejor].get("mrr"), 3),
               f"método {METODOS.get(mejor, (mejor,))[0].lower()}"
               + (f" · peso léxico {ui.num(ev['peso_lexico'], 2)}" if "peso_lexico" in ev else ""), ui.NARANJA),
    ])

    barrido = ev.get("barrido_peso_lexico")
    c1, c2 = st.columns([1.3, 1], gap="large") if barrido else (st.container(), None)
    with c1:
        ui.seccion("Métricas por método", "Mayor es mejor; todas en escala 0–1.")
        fig = go.Figure()
        for m in presentes:
            nombre, color = METODOS.get(m, (m, ui.GRIS))
            vals = [met[m].get(k) for k in METRICAS]
            fig.add_bar(x=[k.upper().replace("HIT", "Hit") for k in METRICAS], y=vals, name=nombre, marker_color=color,
                        text=[ui.num(v, 2) if v is not None else "" for v in vals], textposition="outside",
                        cliponaxis=False, hovertemplate=f"{nombre} · %{{x}}: %{{y:.3f}}<extra></extra>")
        fig.update_layout(barmode="group", yaxis=dict(range=[0, 1.12], title="Valor"), xaxis=dict(title=""))
        ui.grafico(fig, height=380)

    if barrido:
        with c2:
            ui.seccion("Barrido del peso léxico (híbrido)",
                       "Métricas del método híbrido al variar el peso de la componente léxica (0 = solo semántico).")
            if isinstance(barrido, dict):
                bdf = pd.DataFrame([{"peso": float(k), **v} for k, v in barrido.items()])
            else:
                bdf = pd.DataFrame(barrido)
                bdf = bdf.rename(columns={c: "peso" for c in bdf.columns if c in ("peso_lexico", "w", "alpha")})
            bdf = bdf.sort_values("peso")
            fig = go.Figure()
            for k, color in zip(METRICAS, [ui.MORADO, ui.NARANJA, ui.VERDE, ui.AZUL]):
                if k in bdf:
                    fig.add_scatter(x=bdf["peso"], y=bdf[k], name=k.upper().replace("HIT", "Hit"), mode="lines+markers",
                                    line=dict(color=color, width=2.5, dash="dash" if k == "mrr" else "solid"),
                                    hovertemplate=f"peso %{{x}} · {k}: %{{y:.3f}}<extra></extra>")
            if "peso_lexico" in ev:
                fig.add_vline(x=float(ev["peso_lexico"]), line=dict(color=ui.GRIS, dash="dot"),
                              annotation_text="peso elegido", annotation_position="bottom right")
            vmin = float(bdf[[k for k in METRICAS if k in bdf]].min().min())
            fig.update_layout(xaxis=dict(title="Peso léxico"),
                              yaxis=dict(title="Valor", range=[max(0.0, vmin - 0.08), 1.02]))
            ui.grafico(fig, height=380)

    if ev.get("por_categoria"):
        ui.seccion("MRR por categoría de pregunta", "Dónde falla cada método según el tema consultado.")
        filas = [{"categoria": cat, "metodo": METODOS.get(m, (m,))[0], "mrr": v.get("mrr")}
                 for cat, ms in ev["por_categoria"].items() for m, v in ms.items()]
        cdf = pd.DataFrame(filas).pivot(index="metodo", columns="categoria", values="mrr")
        cdf = cdf.reindex([METODOS[m][0] for m in METODOS if METODOS[m][0] in cdf.index])
        fig = go.Figure(go.Heatmap(
            z=cdf.values, x=[c.replace("_", " ") for c in cdf.columns], y=cdf.index, colorscale=ui.ESCALA_MORADA,
            zmin=0, zmax=1, xgap=3, ygap=3, text=[[ui.num(v, 2) for v in r] for r in cdf.values],
            texttemplate="%{text}", colorbar=dict(title=dict(text="MRR"), thickness=12),
            hovertemplate="%{y} · %{x}: MRR %{z:.3f}<extra></extra>",
        ))
        fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=20, b=10))
        ui.grafico(fig, height=260)

    pp = ev.get("por_pregunta") or []
    if pp:
        ui.seccion("Resultado por pregunta", "Posición en la que apareció la fuente esperada (vacío = no recuperada en el top k).")
        qdf = pd.DataFrame(pp)
        cols = [c for c in ["id", "categoria", "pregunta", "esperado", "rank_semantico", "rank_lexico", "rank_hibrido"]
                if c in qdf]
        solo_fallos = st.toggle("Mostrar solo preguntas donde algún método no acierta en primer lugar", key="rag_fallos")
        if solo_fallos:
            ranks = qdf[[c for c in cols if c.startswith("rank_")]]
            qdf = qdf[(ranks.fillna(99) != 1).any(axis=1)]
        st.dataframe(qdf[cols], hide_index=True, column_config={
            "id": "Id", "categoria": "Categoría", "pregunta": st.column_config.TextColumn("Pregunta", width="medium"),
            "esperado": "Documento esperado",
            "rank_semantico": st.column_config.NumberColumn("Semántico", format="%d"),
            "rank_lexico": st.column_config.NumberColumn("Léxico", format="%d"),
            "rank_hibrido": st.column_config.NumberColumn("Híbrido", format="%d"),
        })
else:
    st.info("Aún no hay resultados de evaluación del RAG. Ejecute la evaluación para generar "
            "`rag/eval/resultados.json` (en Docker se monta en `/app/rag_eval/resultados.json`) y vuelva a cargar.",
            icon=":material/fact_check:")

# ---------------------------------------------------------------------------
ui.seccion("Corpus indexado", "Fragmentos almacenados en chatbot.rag_documentos (pgvector, 3072 dimensiones).")
corpus = ui.cargar(datos.corpus_rag)
if corpus.empty:
    st.info("La base vectorial está vacía: ejecute rag/ingest.py para indexar el corpus.")
else:
    ui.kpis([
        ui.KPI("Fragmentos", ui.num(len(corpus)), "chunks con embedding", ui.MORADO),
        ui.KPI("Documentos", ui.num(corpus["documento"].nunique()), f"{ui.num(corpus['fuente'].nunique())} fuentes", ui.AZUL),
        ui.KPI("Longitud mediana", f"{ui.num(corpus['caracteres'].median())} car.",
               f"p90 {ui.num(corpus['caracteres'].quantile(.9))} caracteres", ui.NARANJA),
        ui.KPI("Texto total", f"{ui.num(corpus['caracteres'].sum() / 1000, 0)} mil car.", "contenido indexado", ui.VERDE),
    ])
    c3, c4 = st.columns([1.2, 1], gap="large")
    with c3:
        f = corpus.groupby("fuente").agg(fragmentos=("caracteres", "size"), documentos=("documento", "nunique")) \
                  .sort_values("fragmentos")
        fig = go.Figure(go.Bar(
            x=f["fragmentos"], y=[s[:45] for s in f.index], orientation="h", marker_color=ui.MORADO,
            customdata=f["documentos"], text=f["fragmentos"], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}<br>%{x} fragmentos · %{customdata} documentos<extra></extra>",
        ))
        fig.update_layout(title="Fragmentos por fuente", xaxis=dict(title="Fragmentos"), margin=dict(l=10, r=40, t=48, b=10))
        ui.grafico(fig, height=max(320, 34 * len(f) + 90))
    with c4:
        fig = go.Figure(go.Histogram(x=corpus["caracteres"], nbinsx=30, marker_color=ui.AZUL_MEDIO,
                                     marker_line=dict(color="#FFFFFF", width=1),
                                     hovertemplate="%{x} caracteres: %{y} fragmentos<extra></extra>"))
        fig.add_vline(x=float(corpus["caracteres"].median()), line=dict(color=ui.NARANJA, dash="dash"),
                      annotation_text="mediana", annotation_position="top right")
        fig.update_layout(title="Longitud de los fragmentos", xaxis=dict(title="Caracteres"),
                          yaxis=dict(title="Fragmentos"), bargap=0.05)
        ui.grafico(fig, height=max(320, 34 * corpus["fuente"].nunique() + 90))
