"""Página 7 · Noticias (scraper de unab.edu.co)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402

ui.encabezado(
    "Noticias",
    "Publicaciones de unab.edu.co recolectadas por el scraper periódico y clasificadas por tipo. La relevancia "
    "es un puntaje heurístico para estudiantes de Ingeniería de Sistemas y Competencias Digitales; el chatbot "
    "la usa para recomendar convocatorias, cursos y eventos.",
)

nt = ui.cargar(datos.noticias)
if nt.empty:
    st.info("Aún no hay noticias: ejecute el scraper (scraper/scraper_noticias.py) para poblar chatbot.noticia.",
            icon=":material/newspaper:")
    st.stop()

nt = nt.copy()
nt["fecha"] = nt["fecha_pub"].dt.tz_localize(None)
nt["mes"] = nt["fecha"].dt.to_period("M").dt.to_timestamp()
COLOR_TIPO = {"curso": ui.MORADO, "convocatoria": ui.NARANJA, "certificación": ui.VERDE, "evento": ui.AZUL_MEDIO,
              "general": ui.GRIS}

ahora = pd.Timestamp.now(tz=None)
recientes = nt[nt["fecha"] >= ahora - pd.Timedelta(days=30)]
ultimo_scrape = nt["scrapeado_en"].max()
ui.kpis([
    ui.KPI("Noticias", ui.num(len(nt)), f"desde {nt['fecha'].min():%Y-%m-%d}", ui.AZUL),
    ui.KPI("Últimos 30 días", ui.num(len(recientes)), "publicaciones recientes", ui.MORADO),
    ui.KPI("Relevantes (≥ 3)", ui.num(int((nt["relevancia"].fillna(0) >= 3).sum())), "para Sistemas / CD", ui.NARANJA),
    ui.KPI("Última actualización", f"{ultimo_scrape:%Y-%m-%d}" if pd.notna(ultimo_scrape) else "—",
           f"{ultimo_scrape:%H:%M} (hora Colombia)" if pd.notna(ultimo_scrape) else "", ui.VERDE),
])

tipos = sorted(nt["tipo"].unique().tolist())
sel = st.multiselect("Tipos", tipos, default=tipos, key="tipos_noticias")
f = nt[nt["tipo"].isin(sel)] if sel else nt.iloc[0:0]

c1, c2 = st.columns([1, 1.6], gap="large")
with c1:
    ui.seccion("Noticias por tipo", "Clasificación automática por palabras clave.")
    t = f["tipo"].value_counts().sort_values()
    fig = go.Figure(go.Bar(x=t.values, y=t.index, orientation="h",
                           marker_color=[COLOR_TIPO.get(x, ui.GRIS) for x in t.index],
                           text=t.values, textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x} noticias<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Noticias"), margin=dict(l=10, r=40, t=20, b=10))
    ui.grafico(fig, height=340)

with c2:
    ui.seccion("Publicaciones por mes", "Volumen mensual por tipo de noticia.")
    m = f.groupby(["mes", "tipo"]).size().reset_index(name="n")
    fig = go.Figure()
    for tipo in [x for x in COLOR_TIPO if x in set(m["tipo"])] + [x for x in set(m["tipo"]) if x not in COLOR_TIPO]:
        d = m[m["tipo"] == tipo]
        fig.add_bar(x=d["mes"], y=d["n"], name=tipo, marker_color=COLOR_TIPO.get(tipo, ui.GRIS),
                    hovertemplate=f"{tipo} · %{{x|%b %Y}}: %{{y}}<extra></extra>")
    fig.update_layout(barmode="stack", xaxis=dict(title="", tickformat="%b %Y", dtick="M1"),
                      yaxis=dict(title="Noticias"))
    ui.grafico(fig, height=340)

ui.seccion("Relevancia en el tiempo", "Cada punto es una noticia; los de arriba son los más útiles para el programa.")
fig = go.Figure()
for tipo in sorted(set(f["tipo"])):
    d = f[f["tipo"] == tipo]
    fig.add_scatter(x=d["fecha"], y=d["relevancia"], mode="markers", name=tipo, text=d["titulo"],
                    marker=dict(color=COLOR_TIPO.get(tipo, ui.GRIS), size=10, opacity=0.8, line=dict(color="#FFFFFF", width=1)),
                    hovertemplate="<b>%{text}</b><br>%{x|%Y-%m-%d} · relevancia %{y:.2f}<extra></extra>")
fig.update_layout(xaxis=dict(title=""), yaxis=dict(title="Relevancia", rangemode="tozero"))
ui.grafico(fig, height=320)

ui.seccion("Más relevantes", "Las 15 noticias con mayor puntaje entre los tipos seleccionados.")
top = f.sort_values(["relevancia", "fecha"], ascending=[False, False]).head(15).copy()
top["fecha_txt"] = top["fecha"].dt.strftime("%Y-%m-%d")
st.dataframe(
    top[["fecha_txt", "tipo", "titulo", "relevancia", "url"]],
    hide_index=True,
    column_config={
        "fecha_txt": "Fecha", "tipo": "Tipo", "titulo": st.column_config.TextColumn("Título", width="large"),
        "relevancia": st.column_config.ProgressColumn("Relevancia", format="%.2f", min_value=0,
                                                      max_value=float(max(1.0, nt["relevancia"].max() or 1))),
        "url": st.column_config.LinkColumn("Enlace", display_text="Abrir"),
    },
)
