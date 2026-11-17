"""Identidad visual del Observatorio: paleta UNAB, plantilla Plotly, CSS y tarjetas KPI."""
from __future__ import annotations

import html
from dataclasses import dataclass

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Paleta UNAB
# ---------------------------------------------------------------------------
MORADO = "#8E00E6"
NARANJA = "#F7A600"
AZUL = "#1C2B4A"
VERDE = "#1F7A6E"
FONDO = "#F7F7FB"
ROJO = "#B42318"          # alertas (contraste AA sobre blanco)
GRIS = "#8A93A6"
GRIS_CLARO = "#E4E6EE"
LILA = "#C9A3F2"
AZUL_MEDIO = "#4A6FA5"

SECUENCIA = [MORADO, NARANJA, VERDE, AZUL, AZUL_MEDIO, LILA, "#D9822B", GRIS]

ESTADO_COLOR = {
    "Normal": VERDE,
    "Condicional": NARANJA,
    "En prueba académica": ROJO,
    "Sin calificaciones": GRIS,
}
CONDICION_COLOR = {
    "Activo": VERDE,
    "En reserva de cupo": AZUL_MEDIO,
    "En reintegro": LILA,
    "Inactivo": GRIS,
    "Desertor": ROJO,
    "Retirado": NARANJA,
    "Egresado": AZUL,
    "Graduado": MORADO,
}
NIVEL_COLOR = {"bajo": VERDE, "medio": NARANJA, "alto": ROJO}

FUENTE = "Inter, 'Source Sans Pro', 'Segoe UI', sans-serif"

# Escalas secuenciales/divergentes accesibles
ESCALA_MORADA = [[0, "#F3EAFD"], [0.5, "#B266F0"], [1, "#4B0079"]]
ESCALA_RIESGO = [[0, "#E8F3F1"], [0.35, "#F7D27A"], [0.7, "#F08A24"], [1, ROJO]]

# ---------------------------------------------------------------------------
# Plantilla Plotly (se define una sola vez)
# ---------------------------------------------------------------------------
_PLANTILLA = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FUENTE, size=13, color=AZUL),
        title=dict(font=dict(size=15, color=AZUL), x=0, xanchor="left", y=0.98),
        colorway=SECUENCIA,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=48, b=10),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=GRIS_CLARO, font=dict(family=FUENTE, color=AZUL)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", title=dict(text="")),
        xaxis=dict(gridcolor=GRIS_CLARO, linecolor=GRIS_CLARO, zerolinecolor=GRIS_CLARO,
                   tickfont=dict(color="#4A5468"), title=dict(font=dict(color="#4A5468")), automargin=True),
        yaxis=dict(gridcolor=GRIS_CLARO, linecolor=GRIS_CLARO, zerolinecolor=GRIS_CLARO,
                   tickfont=dict(color="#4A5468"), title=dict(font=dict(color="#4A5468")), automargin=True),
        bargap=0.25,
        separators=",.",
    ),
)
pio.templates["unab"] = _PLANTILLA
pio.templates.default = "plotly_white+unab"

_CONFIG_PLOTLY = {"displaylogo": False, "locale": "es",
                  "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def grafico(fig: go.Figure, height: int | None = None, key: str | None = None) -> None:
    """Renderiza una figura Plotly con la plantilla UNAB (sin el tema de Streamlit)."""
    if height:
        fig.update_layout(height=height)
    st.plotly_chart(fig, theme=None, config=_CONFIG_PLOTLY, key=key)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stCaption {{ font-family: {FUENTE}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1400px; }}
h1, h2, h3 {{ color: {AZUL}; letter-spacing: -0.01em; }}
h1 {{ font-weight: 700; }}

.obs-header {{ margin-bottom: .4rem; }}
.obs-kicker {{ color: {MORADO}; font-weight: 600; font-size: .78rem; text-transform: uppercase;
              letter-spacing: .08em; margin-bottom: .1rem; }}
.obs-title {{ color: {AZUL}; font-size: 2rem; font-weight: 700; line-height: 1.15; margin: 0; }}
.obs-caption {{ color: #4A5468; font-size: .95rem; margin-top: .35rem; max-width: 900px; }}
.obs-rule {{ height: 4px; width: 64px; border-radius: 4px; margin: .7rem 0 1.1rem 0;
            background: linear-gradient(90deg, {MORADO} 0%, {MORADO} 60%, {NARANJA} 60%, {NARANJA} 100%); }}

.kpi {{ background: #FFFFFF; border: 1px solid {GRIS_CLARO}; border-radius: 16px;
        padding: 16px 18px 14px 18px; box-shadow: 0 1px 2px rgba(28,43,74,.06), 0 4px 14px rgba(28,43,74,.04);
        border-top: 4px solid var(--acento, {MORADO}); height: 100%; min-height: 118px; }}
.kpi-label {{ color: #4A5468; font-size: .80rem; font-weight: 600; text-transform: uppercase;
             letter-spacing: .04em; }}
.kpi-value {{ color: {AZUL}; font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-top: .25rem; }}
.kpi-sub {{ color: #5F6B80; font-size: .82rem; margin-top: .2rem; }}

.obs-section {{ color: {AZUL}; font-weight: 650; font-size: 1.12rem; margin: 1.3rem 0 .2rem 0; }}
.obs-note {{ background: #FFFFFF; border-left: 4px solid {NARANJA}; border-radius: 10px;
            padding: 10px 14px; color: #3B4559; font-size: .88rem; }}

section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {AZUL} 0%, #24365C 100%); }}
section[data-testid="stSidebar"] * {{ color: #E9ECF5; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"],
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover {{ background: rgba(142,0,230,.35); }}
section[data-testid="stSidebar"] button {{ background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.25); }}
[data-testid="stSidebarHeader"] {{ height: auto; padding-top: 1.2rem; padding-bottom: .6rem; }}
img[data-testid="stLogo"], [data-testid="stSidebarLogo"] {{ height: 3.1rem; max-width: 230px; width: auto; }}
.obs-brand {{ padding: .2rem 0 1rem 0; border-bottom: 1px solid rgba(255,255,255,.15); margin-bottom: .8rem; }}
.obs-brand-name {{ font-size: 1.35rem; font-weight: 700; color: #FFFFFF !important; letter-spacing: -.01em; }}
.obs-brand-name span {{ color: {NARANJA} !important; }}
.obs-brand-sub {{ font-size: .78rem; color: #C9CFE0 !important; margin-top: .15rem; }}
.obs-footer {{ margin-top: 2.5rem; padding-top: .8rem; border-top: 1px solid {GRIS_CLARO};
              color: #5F6B80; font-size: .8rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: .5rem; }}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
</style>
"""


def estilos() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def barra_lateral() -> None:
    """Marca "UNABot · Observatorio" en la cabecera de la barra lateral (encima de la navegación)."""
    from pathlib import Path

    logo = Path(__file__).resolve().parents[1] / "static" / "logo.svg"
    if logo.is_file():
        st.logo(str(logo), size="large")
    else:  # respaldo en texto
        with st.sidebar:
            st.markdown(
                '<div class="obs-brand"><div class="obs-brand-name">UNABot <span>·</span> Observatorio</div>'
                '<div class="obs-brand-sub">Ingeniería de Sistemas · UNAB</div></div>',
                unsafe_allow_html=True,
            )


def barra_lateral_pie() -> None:
    with st.sidebar:
        st.divider()
        if st.button("Actualizar datos", icon=":material/refresh:", width="stretch",
                     help="Limpia la caché (5 min) y vuelve a consultar la base de datos"):
            st.cache_data.clear()
            st.rerun()
        st.caption("Datos sintéticos — simulación Banner/COSMOS")


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------
def encabezado(titulo: str, descripcion: str, kicker: str = "Observatorio académico UNABot") -> None:
    st.markdown(
        f'<div class="obs-header"><div class="obs-kicker">{html.escape(kicker)}</div>'
        f'<h1 class="obs-title">{html.escape(titulo)}</h1>'
        f'<div class="obs-caption">{html.escape(descripcion)}</div><div class="obs-rule"></div></div>',
        unsafe_allow_html=True,
    )


def seccion(titulo: str, ayuda: str | None = None) -> None:
    st.markdown(f'<div class="obs-section">{html.escape(titulo)}</div>', unsafe_allow_html=True)
    if ayuda:
        st.caption(ayuda)


def nota(texto: str) -> None:
    st.markdown(f'<div class="obs-note">{html.escape(texto)}</div>', unsafe_allow_html=True)


@dataclass
class KPI:
    etiqueta: str
    valor: str
    detalle: str = ""
    acento: str = MORADO


def kpis(items: list[KPI]) -> None:
    cols = st.columns(len(items))
    for col, k in zip(cols, items):
        col.markdown(
            f'<div class="kpi" style="--acento:{k.acento}">'
            f'<div class="kpi-label">{html.escape(k.etiqueta)}</div>'
            f'<div class="kpi-value">{html.escape(k.valor)}</div>'
            f'<div class="kpi-sub">{html.escape(k.detalle)}</div></div>',
            unsafe_allow_html=True,
        )


def pie_pagina() -> None:
    st.markdown(
        '<div class="obs-footer"><span>Datos sintéticos — simulación Banner/COSMOS</span>'
        "<span>Chatbot de apoyo académico · Ingeniería de Sistemas UNAB</span></div>",
        unsafe_allow_html=True,
    )


def cargar(fn, *args, **kwargs):
    """Ejecuta una consulta; ante un error de conexión muestra un aviso y detiene la página."""
    import psycopg

    from .db import ConfigError

    try:
        return fn(*args, **kwargs)
    except ConfigError as e:
        st.error(str(e), icon=":material/key_off:")
    except psycopg.errors.QueryCanceled:
        st.error("La consulta superó el tiempo máximo permitido (8 s). Intente de nuevo en unos segundos.",
                 icon=":material/timer_off:")
    except psycopg.Error as e:
        st.error(f"No fue posible consultar la base de datos ({type(e).__name__}).", icon=":material/cloud_off:")
    pie_pagina()
    st.stop()


# ---------------------------------------------------------------------------
# Formato numérico (convención colombiana: coma decimal)
# ---------------------------------------------------------------------------
def num(x: float | int | None, dec: int = 0) -> str:
    if x is None or x != x:  # NaN
        return "—"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x: float | None, dec: int = 1) -> str:
    return "—" if x is None or x != x else f"{num(x, dec)} %"


def enmascarar_codigo(codigo: str | None) -> str:
    if not codigo:
        return "—"
    c = str(codigo)
    return c[:3] + "*" * max(0, len(c) - 5) + c[-2:] if len(c) > 5 else "***"
