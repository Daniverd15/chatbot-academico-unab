"""Página 2 · Cursos y cuellos de botella."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from collections import defaultdict, deque  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402

ui.encabezado(
    "Cursos y cuellos de botella",
    "Qué cursos concentran la reprobación y cuáles frenan el avance porque son prerrequisito en cadena de "
    "muchos otros. Un curso con alta reprobación y muchos dependientes es un cuello de botella del plan.",
)

est = ui.cargar(datos.estadistica_cursos)
rep = ui.cargar(datos.reprobacion_curso_periodo)
pre = ui.cargar(datos.prerrequisitos)

est = est.copy()
est["tasa_reprobacion"] = est["tasa_reprobacion"].fillna(0.0)
est["indice_cuello"] = est["tasa_reprobacion"] / 100 * est["cursos_que_bloquea"]
est["etiqueta"] = est["curso_id"] + " · " + est["curso"]
evaluados = est[est["intentos"] > 0]

peor = evaluados.sort_values("tasa_reprobacion", ascending=False).head(1)
cuello = est.sort_values("indice_cuello", ascending=False).head(1)
media_pond = (np.average(evaluados["tasa_reprobacion"], weights=evaluados["intentos"])
              if len(evaluados) else None)

ui.kpis([
    ui.KPI("Cursos del plan", ui.num(len(est)), f"{ui.num(len(pre[pre['tipo'] == 'prerrequisito']))} relaciones de prerrequisito", ui.AZUL),
    ui.KPI("Reprobación global", ui.pct(media_pond), "ponderada por intentos evaluados", ui.ROJO),
    ui.KPI("Curso más reprobado", peor["curso_id"].iloc[0] if len(peor) else "—",
           f"{peor['curso'].iloc[0]} · {ui.pct(peor['tasa_reprobacion'].iloc[0])}" if len(peor) else "", ui.NARANJA),
    ui.KPI("Mayor cuello de botella", cuello["curso_id"].iloc[0] if len(cuello) else "—",
           f"{cuello['curso'].iloc[0]} · bloquea {int(cuello['cursos_que_bloquea'].iloc[0])}" if len(cuello) else "",
           ui.MORADO),
])

# ---------------------------------------------------------------------------
ui.seccion("Tasa de reprobación por curso y periodo",
           "Porcentaje de estudiantes evaluados que reprobaron. Filas ordenadas por semestre sugerido del plan.")
semestres = sorted(est["semestre_sugerido"].unique().tolist())
sel = st.multiselect("Semestres del plan", semestres, default=semestres[:5] if len(semestres) > 5 else semestres,
                     format_func=lambda s: f"Semestre {s}", key="sem_heatmap")
if rep.empty or not sel:
    st.info("Seleccione al menos un semestre con calificaciones registradas.")
else:
    r = rep[rep["semestre_sugerido"].isin(sel)].copy()
    r["etiqueta"] = r["curso_id"] + " · " + r["curso"].str.slice(0, 34)
    orden_filas = (r[["etiqueta", "semestre_sugerido", "curso_id"]].drop_duplicates()
                   .sort_values(["semestre_sugerido", "curso_id"])["etiqueta"].tolist())
    periodos = sorted(r["periodo_id"].unique().tolist())
    z = r.pivot(index="etiqueta", columns="periodo_id", values="tasa_reprobacion").reindex(index=orden_filas, columns=periodos)
    n = r.pivot(index="etiqueta", columns="periodo_id", values="evaluados").reindex(index=orden_filas, columns=periodos)
    fig = go.Figure(go.Heatmap(
        z=z.values, x=periodos, y=orden_filas, customdata=n.values, colorscale=ui.ESCALA_RIESGO, zmin=0,
        zmax=max(40.0, float(np.nanmax(z.values)) if np.isfinite(z.values).any() else 40.0),
        xgap=2, ygap=2, colorbar=dict(title=dict(text="% reprob."), ticksuffix=" %", thickness=12),
        hovertemplate="%{y}<br>Periodo %{x}: %{z:.1f} % (%{customdata} evaluados)<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(autorange="reversed", tickfont=dict(size=11)), xaxis=dict(type="category", side="top"),
                      margin=dict(l=10, r=10, t=30, b=10))
    ui.grafico(fig, height=max(320, 26 * len(orden_filas) + 80))

# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.35, 1], gap="large")
with c1:
    ui.seccion("Nota promedio vs. tasa de reprobación",
               "El tamaño del círculo indica cuántos cursos bloquea en cadena; el color, el semestre sugerido.")
    d = evaluados
    fig = go.Figure(go.Scatter(
        x=d["nota_promedio"], y=d["tasa_reprobacion"], mode="markers",
        marker=dict(size=8 + 5 * np.sqrt(d["cursos_que_bloquea"]), sizemode="diameter", color=d["semestre_sugerido"],
                    colorscale=ui.ESCALA_MORADA, cmin=1, cmax=max(9, int(d["semestre_sugerido"].max() or 9)),
                    line=dict(color="#FFFFFF", width=1.2), opacity=0.88,
                    colorbar=dict(title=dict(text="Semestre"), thickness=12, dtick=1)),
        text=d["etiqueta"], customdata=np.stack([d["cursos_que_bloquea"], d["intentos"]], axis=-1),
        hovertemplate="<b>%{text}</b><br>Nota promedio %{x:.2f} · Reprobación %{y:.1f} %"
                      "<br>Bloquea %{customdata[0]} cursos · %{customdata[1]} intentos<extra></extra>",
    ))
    top_lbl = d.sort_values("indice_cuello", ascending=False).head(5)
    for _, row in top_lbl.iterrows():
        fig.add_annotation(x=row["nota_promedio"], y=row["tasa_reprobacion"], text=row["curso_id"], showarrow=False,
                           yshift=8 + 2.5 * np.sqrt(row["cursos_que_bloquea"]), font=dict(size=11, color=ui.AZUL))
    fig.add_vline(x=3.0, line=dict(color=ui.ROJO, dash="dot", width=1.5))
    fig.update_layout(xaxis=dict(title="Nota promedio (0–5)"), yaxis=dict(title="Tasa de reprobación", ticksuffix=" %"))
    ui.grafico(fig, height=440)

with c2:
    ui.seccion("Top 10 cuellos de botella",
               "Índice = tasa de reprobación × cursos que bloquea: estudiantes-curso “frenados” por cada 1 que intenta.")
    t = est.sort_values("indice_cuello", ascending=False).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=t["indice_cuello"], y=t["curso_id"] + " · " + t["curso"].str.slice(0, 26), orientation="h",
        marker=dict(color=t["indice_cuello"], colorscale=[[0, ui.LILA], [1, ui.MORADO]]),
        customdata=np.stack([t["tasa_reprobacion"], t["cursos_que_bloquea"]], axis=-1),
        text=[ui.num(v, 2) for v in t["indice_cuello"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Reprobación %{customdata[0]:.1f} % × bloquea %{customdata[1]}<br>Índice %{x:.2f}<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(title="Índice de cuello de botella"), yaxis=dict(tickfont=dict(size=11)),
                      margin=dict(l=10, r=40, t=20, b=10))
    ui.grafico(fig, height=440)

# ---------------------------------------------------------------------------
ui.seccion("Mapa de prerrequisitos del plan",
           "Cada columna es un semestre sugerido; las flechas van del prerrequisito al curso que habilita. "
           "Color = tasa de reprobación, tamaño = cursos bloqueados en cadena. Elija un curso para resaltar su cadena.")

cursos = est.set_index("curso_id")
aristas = pre[(pre["tipo"].isin(["prerrequisito", "correquisito"])) & pre["requisito_id"].notna()
              & pre["requisito_id"].isin(cursos.index) & pre["curso_id"].isin(cursos.index)]
cred_min = pre[pre["tipo"] == "creditos"].groupby("curso_id")["creditos_min"].max()

hijos, padres = defaultdict(set), defaultdict(set)
for a in aristas.itertuples():
    hijos[a.requisito_id].add(a.curso_id)
    padres[a.curso_id].add(a.requisito_id)

# Disposición por capas con heurística de baricentro para reducir cruces.
pos: dict[str, tuple[float, float]] = {}
for s in sorted(cursos["semestre_sugerido"].unique()):
    ids = cursos[cursos["semestre_sugerido"] == s].index.tolist()

    def _bary(c):
        ys = [pos[p][1] for p in padres[c] if p in pos]
        return (0, float(np.mean(ys))) if ys else (1, 0.0)

    ids.sort(key=lambda c: (_bary(c), c))
    k = len(ids)
    for i, c in enumerate(ids):
        pos[c] = (float(s), (k - 1) / 2 - i)


def _alcanzables(inicio: str, grafo: dict) -> set:
    vistos, cola = set(), deque([inicio])
    while cola:
        for n in grafo[cola.popleft()]:
            if n not in vistos:
                vistos.add(n)
                cola.append(n)
    return vistos


opciones = ["(ninguno)"] + cursos.sort_values(["semestre_sugerido"]).index.tolist()
foco = st.selectbox("Resaltar cadena de", opciones, index=0, key="foco_grafo",
                    format_func=lambda c: c if c == "(ninguno)" else f"{c} · {cursos.loc[c, 'curso']}")
if foco != "(ninguno)":
    anc, desc = _alcanzables(foco, padres), _alcanzables(foco, hijos)
    activos = anc | desc | {foco}
else:
    anc, desc, activos = set(), set(), set(cursos.index)

fig = go.Figure()
for a in aristas.itertuples():
    (x0, y0), (x1, y1) = pos[a.requisito_id], pos[a.curso_id]
    aguas_abajo = a.requisito_id in desc | {foco} and a.curso_id in desc
    aguas_arriba = a.curso_id in anc | {foco} and a.requisito_id in anc
    if foco == "(ninguno)":
        color, ancho = "rgba(28,43,74,.28)", 1.1
    elif aguas_abajo:
        color, ancho = ui.NARANJA, 2.2
    elif aguas_arriba:
        color, ancho = ui.MORADO, 2.2
    else:
        color, ancho = "rgba(28,43,74,.07)", 1
    fig.add_annotation(x=x1 - 0.09, y=y1, ax=x0 + 0.09, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=ancho, arrowcolor=color, text="",
                       standoff=4)

ids = cursos.index.tolist()
xs, ys = [pos[c][0] for c in ids], [pos[c][1] for c in ids]
opac = [1.0 if c in activos else 0.18 for c in ids]
hover = []
for c in ids:
    row = cursos.loc[c]
    reqs = ", ".join(sorted(padres[c])) or "ninguno"
    extra = f"<br>Requiere ≥ {int(cred_min[c])} créditos aprobados" if c in cred_min.index else ""
    hover.append(f"<b>{c} · {row['curso']}</b><br>Semestre {row['semestre_sugerido']} · {row['creditos']} créditos"
                 f"<br>Reprobación {row['tasa_reprobacion']:.1f} % · bloquea {int(row['cursos_que_bloquea'])}"
                 f"<br>Prerrequisitos: {reqs}{extra}")
fig.add_scatter(
    x=xs, y=ys, mode="markers+text", text=[c for c in ids], textposition="bottom center",
    textfont=dict(size=10, color=ui.AZUL), hovertext=hover, hoverinfo="text",
    marker=dict(size=[12 + 4.5 * np.sqrt(cursos.loc[c, "cursos_que_bloquea"]) for c in ids], color=cursos["tasa_reprobacion"],
                colorscale=ui.ESCALA_RIESGO, cmin=0, cmax=max(30.0, float(cursos["tasa_reprobacion"].max())),
                opacity=opac, line=dict(color=[ui.AZUL if c == foco else "#FFFFFF" for c in ids],
                                        width=[3 if c == foco else 1.5 for c in ids]),
                colorbar=dict(title=dict(text="% reprob."), ticksuffix=" %", thickness=12)),
    showlegend=False,
)
alto = max(abs(y) for y in ys) if ys else 3
fig.update_layout(
    xaxis=dict(title="", tickmode="array", tickvals=semestres, ticktext=[f"Semestre {s}" for s in semestres],
               side="top", showgrid=False, zeroline=False, range=[min(semestres) - 0.6, max(semestres) + 0.6]),
    yaxis=dict(visible=False, range=[-alto - 0.9, alto + 0.7]),
    plot_bgcolor="#FFFFFF", margin=dict(l=10, r=10, t=40, b=10),
)
ui.grafico(fig, height=max(480, int(95 * (2 * alto + 1.6))))
if foco != "(ninguno)":
    st.caption(f"{foco}: {len(anc)} cursos previos en su cadena (morado) y {len(desc)} cursos que dependen de él (naranja).")

# ---------------------------------------------------------------------------
with st.expander("Tabla completa de cursos"):
    st.dataframe(
        est[["curso_id", "curso", "semestre_sugerido", "creditos", "componente", "intentos", "nota_promedio",
             "tasa_reprobacion", "cursos_que_bloquea", "indice_cuello"]].sort_values("indice_cuello", ascending=False),
        hide_index=True,
        column_config={
            "curso_id": "Código", "curso": "Curso", "semestre_sugerido": "Semestre", "creditos": "Créditos",
            "componente": "Componente", "intentos": "Intentos",
            "nota_promedio": st.column_config.NumberColumn("Nota prom.", format="%.2f"),
            "tasa_reprobacion": st.column_config.ProgressColumn("Reprobación", format="%.1f %%", min_value=0, max_value=100),
            "cursos_que_bloquea": "Bloquea",
            "indice_cuello": st.column_config.NumberColumn("Índice cuello", format="%.2f"),
        },
    )
