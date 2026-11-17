"""Acceso de solo lectura a PostgreSQL (Supabase) para el Observatorio.

* La cadena de conexión se toma de ``DASH_DATABASE_URL`` y, si no existe, de
  ``MCP_DATABASE_URL`` (rol ``mcp_readonly``). En local se carga ``../.env``.
* La conexión se cachea con ``st.cache_resource`` y se reabre si se cae.
* Los resultados se cachean 5 minutos con ``st.cache_data(ttl=300)``.
* ``prepare_threshold=None`` desactiva las sentencias preparadas, necesario
  detrás del pooler de Supabase (modo transacción).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.types.numeric import FloatLoader

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DASHBOARD_DIR.parent

# .env del repositorio (ejecución local) y, si existe, uno propio del dashboard.
load_dotenv(REPO_ROOT / ".env")
load_dotenv(DASHBOARD_DIR / ".env")

TZ = "America/Bogota"
_lock = threading.Lock()


class ConfigError(RuntimeError):
    """No hay cadena de conexión configurada."""


def _url() -> str:
    url = os.environ.get("DASH_DATABASE_URL") or os.environ.get("MCP_DATABASE_URL")
    if not url:
        raise ConfigError(
            "No se encontró DASH_DATABASE_URL ni MCP_DATABASE_URL. Defina una de las dos "
            "variables (rol de solo lectura) para conectar el Observatorio a la base de datos."
        )
    return url


def _connect() -> psycopg.Connection:
    conn = psycopg.connect(
        _url(),
        autocommit=True,
        prepare_threshold=None,
        connect_timeout=10,
        application_name="unabot-observatorio",
    )
    # NUMERIC -> float (evita Decimal en pandas/plotly)
    conn.adapters.register_loader("numeric", FloatLoader)
    return conn


@st.cache_resource(show_spinner=False)
def _conexion() -> dict:
    # Se guarda en un dict mutable para poder reemplazar la conexión si se cae.
    return {"conn": _connect()}


def _ejecutar(sql: str, params: tuple | dict | None) -> pd.DataFrame:
    holder = _conexion()
    with _lock:
        for intento in (1, 2):
            conn = holder["conn"]
            try:
                if conn.closed or conn.broken:
                    raise psycopg.OperationalError("conexión cerrada")
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    if cur.description is None:
                        return pd.DataFrame()
                    cols = [d.name for d in cur.description]
                    return pd.DataFrame(cur.fetchall(), columns=cols)
            except psycopg.OperationalError:
                if intento == 2:
                    raise
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                holder["conn"] = _connect()
    return pd.DataFrame()  # inalcanzable


@st.cache_data(ttl=300, show_spinner="Consultando la base de datos…")
def consulta(sql: str, params: tuple | None = None) -> pd.DataFrame:
    """Ejecuta una consulta SELECT y devuelve un DataFrame (cacheado 5 min)."""
    df = _ejecutar(sql, params)
    for c in df.columns:
        if isinstance(df[c].dtype, pd.DatetimeTZDtype):
            df[c] = df[c].dt.tz_convert(TZ)
    return df
