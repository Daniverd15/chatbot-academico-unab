"""Aplicación vectorizada del modelo logístico de riesgo académico.

Replica exactamente ``mcp_server/server.py::_riesgo_academico``:
    periodos = max(1, periodos_cursados)
    pga_ultimo_periodo = pga_ultimo_periodo or pga_acumulado
    reprobados_por_periodo = total_reprobados / periodos
    creditos_por_periodo   = creditos_aprobados / periodos
    trabaja = 1/0
    z = intercepto + sum(coef_k * (x_k - media_k) / desv_k);  p = 1 / (1 + e^-z)
    nivel: alto (p >= 0.5), medio (p >= 0.25), bajo
Los estudiantes sin PGA acumulado no reciben probabilidad.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from .db import DASHBOARD_DIR, REPO_ROOT

ETIQUETAS = {
    "pga_acumulado": "PGA acumulado",
    "pga_ultimo_periodo": "PGA último periodo",
    "reprobados_por_periodo": "Reprobados por periodo",
    "creditos_por_periodo": "Créditos aprobados por periodo",
    "trabaja": "Trabaja",
}


def _candidatos_modelo() -> list[Path]:
    rutas = []
    if os.environ.get("DASH_MODELO_RIESGO"):
        rutas.append(Path(os.environ["DASH_MODELO_RIESGO"]))
    rutas += [DASHBOARD_DIR / "modelo_riesgo.json", REPO_ROOT / "mcp_server" / "modelo_riesgo.json"]
    return rutas


@st.cache_data(ttl=300, show_spinner=False)
def cargar_modelo() -> dict | None:
    for p in _candidatos_modelo():
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def features(df: pd.DataFrame) -> pd.DataFrame:
    periodos = df["periodos_cursados"].fillna(0).clip(lower=1).astype(float)
    pga = df["pga_acumulado"].astype(float)
    ultimo = df["pga_ultimo_periodo"].astype(float)
    # `r["pga_ultimo_periodo"] or r["pga_acumulado"]`: None o 0 -> PGA acumulado
    ultimo = ultimo.where(ultimo.notna() & (ultimo != 0), pga)
    return pd.DataFrame({
        "pga_acumulado": pga,
        "pga_ultimo_periodo": ultimo,
        "reprobados_por_periodo": df["total_reprobados"].fillna(0).astype(float) / periodos,
        "creditos_por_periodo": df["creditos_aprobados"].fillna(0).astype(float) / periodos,
        "trabaja": df["trabaja"].fillna(False).astype(bool).astype(float),
    }, index=df.index)


def puntuar(df: pd.DataFrame, modelo: dict) -> pd.DataFrame:
    """Agrega `probabilidad` y `nivel` a los estudiantes con PGA acumulado."""
    out = df[df["pga_acumulado"].notna()].copy()
    X = features(out)
    z = np.full(len(out), float(modelo["intercepto"]))
    for k, coef in modelo["coeficientes"].items():
        col = X[k] if k in X else pd.Series(0.0, index=out.index)
        z += coef * (col.to_numpy() - modelo["medias"][k]) / modelo["desviaciones"][k]
    p = 1.0 / (1.0 + np.exp(-z))
    out["probabilidad"] = np.round(p, 3)
    out["nivel"] = np.select([p >= 0.5, p >= 0.25], ["alto", "medio"], default="bajo")
    for k in X.columns:
        out[f"f_{k}"] = X[k]
    return out
