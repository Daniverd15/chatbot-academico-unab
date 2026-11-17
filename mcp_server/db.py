"""Acceso a PostgreSQL (Supabase) con pool de conexiones y consultas parametrizadas."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None
CODIGO_RE = re.compile(r"^U\d{8}$", re.IGNORECASE)


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        url = os.environ.get("MCP_DATABASE_URL")
        if not url and os.environ.get("MCP_ALLOW_OWNER_DB") == "1":
            url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "Falta MCP_DATABASE_URL (rol de solo lectura mcp_readonly). Para usar la conexión del "
                "propietario en desarrollo define MCP_ALLOW_OWNER_DB=1."
            )
        _pool = ConnectionPool(
            url,
            min_size=1,
            max_size=int(os.environ.get("DB_POOL_MAX", "5")),
            kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
            open=True,
        )
    return _pool


def _clean(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def query(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return []
        return [{k: _clean(v) for k, v in row.items()} for row in cur.fetchall()]


def one(sql: str, params: tuple | dict | None = None) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def normalizar_codigo(codigo: str) -> str:
    """Valida el formato del código estudiantil UNAB (U + 8 dígitos)."""
    c = (codigo or "").strip().upper()
    if not CODIGO_RE.match(c):
        raise ValueError(
            f"Código estudiantil inválido: '{codigo}'. Debe tener el formato U00123456 (U seguida de 8 dígitos)."
        )
    return c
