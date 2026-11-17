"""Página 4 · Competencias digitales (Centro de Competencias Digitales, CCD)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402

ui.encabezado(
    "Competencias digitales",
    "Avance de los estudiantes activos en las tres rutas del Centro de Competencias Digitales: Ruta 1 "
    "(Competencias Digitales Básicas, obligatoria), Ruta 2 (Analítica y Contenido Digital) y Ruta 3 "
    "(Tecnología Transformativa). Quien completa las tres obtiene la insignia digital, requisito de grado.",
)

rutas = ui.cargar(datos.cumplimiento_rutas)
por_est = ui.cargar(datos.rutas_por_estudiante)
prueba = ui.cargar(datos.prueba_diagnostica)
cursos = ui.cargar(datos.cursos_cd)

n_rutas = max(1, len(rutas))
insignia = 100 * (por_est["rutas_cumplidas"] >= n_rutas).mean() if len(por_est) else None
pct_valida = 100 * (prueba["puntaje"] >= 70).mean() if len(prueba) else None
r1 = rutas.loc[rutas["ruta"] == 1, "pct_cumplida"]

ui.kpis([
    ui.KPI("Insignia lista", ui.pct(insignia), f"activos con las {n_rutas} rutas cumplidas", ui.MORADO),
    ui.KPI("Ruta 1 cumplida", ui.pct(r1.iloc[0] if len(r1) else None), "Competencias Digitales Básicas", ui.VERDE),
    ui.KPI("Rutas promedio", ui.num(por_est["rutas_cumplidas"].mean() if len(por_est) else None, 2),
           f"de {n_rutas} por estudiante activo", ui.AZUL),
    ui.KPI("Prueba diagnóstica ≥ 70", ui.pct(pct_valida), f"{ui.num(len(prueba))} estudiantes la presentaron", ui.NARANJA),
])

# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.2, 1], gap="large")
with c1:
    ui.seccion("Cumplimiento por ruta", "Porcentaje de estudiantes activos con la ruta aprobada o en curso.")
    etiquetas = [f"Ruta {int(r.ruta)} · {r.ruta_nombre}" for r in rutas.itertuples()]
    fig = go.Figure()
    fig.add_bar(y=etiquetas, x=rutas["pct_cumplida"], name="Cumplida", orientation="h", marker_color=ui.VERDE,
                text=[ui.pct(v) for v in rutas["pct_cumplida"]], textposition="inside",
                hovertemplate="%{y}: %{x:.1f} % cumplida<extra></extra>")
    fig.add_bar(y=etiquetas, x=rutas["pct_en_curso"], name="En curso", orientation="h", marker_color=ui.NARANJA,
                hovertemplate="%{y}: %{x:.1f} % en curso<extra></extra>")
    resto = 100 - rutas["pct_cumplida"] - rutas["pct_en_curso"]
    fig.add_bar(y=etiquetas, x=resto, name="Pendiente", orientation="h", marker_color=ui.GRIS_CLARO,
                hovertemplate="%{y}: %{x:.1f} % pendiente<extra></extra>")
    fig.update_layout(barmode="stack", xaxis=dict(range=[0, 100], ticksuffix=" %", title="% de activos"),
                      yaxis=dict(autorange="reversed"))
    ui.grafico(fig, height=320)

with c2:
    ui.seccion("Rutas cumplidas por estudiante", "Cuántas de las tres rutas tiene aprobadas cada activo.")
    dist = por_est["rutas_cumplidas"].value_counts().reindex(range(0, n_rutas + 1), fill_value=0)
    fig = go.Figure(go.Bar(
        x=[f"{i} ruta{'s' if i != 1 else ''}" for i in dist.index], y=dist.values,
        marker_color=[ui.MORADO if i == n_rutas else ui.LILA for i in dist.index],
        text=dist.values, textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y} estudiantes<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(title="Estudiantes"), xaxis=dict(title=""))
    ui.grafico(fig, height=320)

# ---------------------------------------------------------------------------
c3, c4 = st.columns([1, 1.2], gap="large")
with c3:
    ui.seccion("Prueba diagnóstica", "Un puntaje de 70 o más valida el curso de la Ruta 1 sin cursarlo.")
    fig = go.Figure()
    fig.add_vrect(x0=70, x1=100, fillcolor=ui.VERDE, opacity=0.07, line_width=0)
    fig.add_histogram(x=prueba["puntaje"], xbins=dict(start=0, end=100, size=5), marker_color=ui.AZUL_MEDIO,
                      marker_line=dict(color="#FFFFFF", width=1), hovertemplate="%{x}: %{y} estudiantes<extra></extra>")
    fig.add_vline(x=70, line=dict(color=ui.VERDE, width=2, dash="dash"))
    fig.add_annotation(x=70, y=1, yref="paper", text="70 · valida Ruta 1", showarrow=False, xanchor="left", xshift=4,
                       font=dict(color=ui.VERDE))
    fig.update_layout(showlegend=False, bargap=0.05, xaxis=dict(title="Puntaje (0–100)", range=[0, 100]),
                      yaxis=dict(title="Estudiantes"))
    ui.grafico(fig, height=360)

with c4:
    ui.seccion("Cursos más tomados", "Inscripciones por curso del CCD y su resultado (incluye la oferta anterior a 2026).")
    if cursos.empty:
        st.info("Aún no hay inscripciones registradas en cursos del CCD.")
    else:
        tot = cursos.groupby("nombre")["inscripciones"].sum().sort_values()
        orden = tot.index.tolist()[-12:]
        colores = {"Aprobado": ui.VERDE, "Validado por prueba": ui.AZUL_MEDIO, "Cursando": ui.NARANJA,
                   "Inscrito": ui.LILA, "Reprobado": ui.ROJO}
        fig = go.Figure()
        for estado, color in colores.items():
            d = cursos[(cursos["estado"] == estado) & cursos["nombre"].isin(orden)].set_index("nombre")["inscripciones"]
            if d.empty:
                continue
            d = d.groupby(level=0).sum().reindex(orden, fill_value=0)
            fig.add_bar(y=[n[:42] for n in d.index], x=d.values, name=estado, orientation="h", marker_color=color,
                        hovertemplate=f"%{{y}}<br>{estado}: %{{x}}<extra></extra>")
        fig.update_layout(barmode="stack", xaxis=dict(title="Inscripciones"), yaxis=dict(tickfont=dict(size=11)))
        ui.grafico(fig, height=360)

# ---------------------------------------------------------------------------
ui.seccion("Insignia lista por cohorte", "Porcentaje de activos de cada cohorte con las tres rutas cumplidas.")
coh = por_est.groupby("cohorte").agg(insignia=("rutas_cumplidas", lambda s: 100 * (s >= n_rutas).mean()),
                                     n=("codigo", "size")).reset_index().sort_values("cohorte")
fig = go.Figure(go.Scatter(
    x=coh["cohorte"], y=coh["insignia"], mode="lines+markers+text", line=dict(color=ui.MORADO, width=3),
    marker=dict(size=9), text=[ui.pct(v, 0) for v in coh["insignia"]], textposition="top center",
    customdata=coh["n"], hovertemplate="Cohorte %{x}: %{y:.1f} % (%{customdata} activos)<extra></extra>",
))
fig.update_layout(xaxis=dict(type="category", title="Cohorte de ingreso"),
                  yaxis=dict(title="% con insignia lista", ticksuffix=" %", range=[0, 105]))
ui.grafico(fig, height=320)
