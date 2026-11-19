"""
Crea el esquema, vistas y funciones, y carga los datos sintéticos en PostgreSQL
(Supabase o local). Idempotente: borra y recrea los esquemas `academico` y `chatbot`.

Uso:
    python database/load_database.py              # usa DATABASE_URL de .env
    python database/load_database.py --skip-rag   # conserva la tabla rag (no implementado: siempre recrea)
"""
from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql as psql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database"
SYN = ROOT / "data" / "synthetic"
load_dotenv(ROOT / ".env")

ORDEN = [
    ("academico.programa", "programa"),
    ("academico.periodo", "periodo"),
    ("academico.curso", "curso"),
    ("academico.prerrequisito", "prerrequisito"),
    ("academico.requisito_grado", "requisito_grado"),
    ("academico.cd_curso", "cd_curso"),
    ("academico.estudiante", "estudiante"),
    ("academico.matricula", "matricula"),
    ("academico.inscripcion", "inscripcion"),
    ("academico.estudiante_requisito", "estudiante_requisito"),
    ("academico.cd_inscripcion", "cd_inscripcion"),
    ("academico.cd_prueba_diagnostica", "cd_prueba_diagnostica"),
]


def copy_csv(cur: psycopg.Cursor, table: str, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    header = next(csv.reader(io.StringIO(text)))
    cols = ", ".join(header)
    with cur.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')") as cp:
        cp.write(text)
    return text.count("\n") - 1


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Falta DATABASE_URL en .env")
    with psycopg.connect(url, autocommit=False) as conn, conn.cursor() as cur:
        scripts = ["01_schema.sql", "02_views.sql", "03_functions_security.sql", "04_alertas_tempranas.sql", "05_memoria_chat.sql",
                   "06_noticias_temas.sql"]
        for f in [s for s in scripts if (DB / s).exists()]:
            print(f"→ ejecutando {f}")
            cur.execute("SET search_path = public, extensions;")
            cur.execute((DB / f).read_text(encoding="utf-8"))
        cur.execute("SET search_path = public, extensions;")
        for table, name in ORDEN:
            n = copy_csv(cur, table, SYN / f"{name}.csv")
            print(f"  {table:<36} {n:>6} filas")
        # calendario espejo
        cal = (ROOT / "data" / "calendario_academico.csv").read_text(encoding="utf-8")
        with cur.copy("COPY chatbot.calendario (periodo_id, categoria, evento, fecha_inicio, fecha_fin, publico, fuente) "
                      "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')") as cp:
            cp.write(cal)
        pw = os.environ.get("MCP_DB_PASSWORD")
        if pw:
            cur.execute(psql.SQL("ALTER ROLE mcp_readonly WITH LOGIN PASSWORD {}").format(psql.Literal(pw)))
            print("  rol mcp_readonly con contraseña asignada")
        conn.commit()

        cur.execute("SELECT * FROM academico.v_indicadores_programa")
        cols = [d.name for d in cur.description]
        print("\nIndicadores del programa:", dict(zip(cols, cur.fetchone())))
        cur.execute("""SELECT codigo, nombre_completo, creditos_aprobados, porcentaje_avance, pga_acumulado,
                              estado_academico, estado_matricula_actual
                       FROM academico.v_estudiante_resumen WHERE codigo LIKE 'U001000%' ORDER BY codigo""")
        print("\nCuentas demo (PIN 1234):")
        for r in cur.fetchall():
            print("  ", r)


if __name__ == "__main__":
    main()
