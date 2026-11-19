"""Consultas del Observatorio. Todas son agregadas o acotadas (statement_timeout = 8 s).

Nota de privacidad: ``academico.estudiante`` tiene permisos por columna; aquí
solo se leen columnas autorizadas y los nombres se enmascaran en SQL, de modo
que el nombre completo nunca sale de la base de datos.
"""
from __future__ import annotations

import pandas as pd

from .db import consulta


# ---------------------------------------------------------------------------
# Panorama
# ---------------------------------------------------------------------------
def indicadores() -> dict:
    df = consulta("SELECT * FROM academico.v_indicadores_programa")
    return df.iloc[0].to_dict() if not df.empty else {}


def resumen_estudiantes() -> pd.DataFrame:
    """Una fila por estudiante (420 aprox.) con los campos analíticos, sin datos de contacto."""
    return consulta(
        """SELECT r.codigo, r.cohorte, r.condicion, r.trabaja, COALESCE(r.beca, 'Sin beca') AS beca,
                  r.periodos_cursados, r.semestre_por_creditos, r.creditos_aprobados, r.porcentaje_avance,
                  r.total_reprobados, r.pga_acumulado, r.pga_ultimo_periodo, r.estado_academico,
                  r.ultimo_periodo_evaluado,
                  upper(left(e.nombres, 1)) || '*** ' || upper(left(e.apellidos, 1)) || '***' AS nombre_enmascarado,
                  e.genero, e.colegio_tipo
           FROM academico.v_estudiante_resumen r
           JOIN academico.estudiante e ON e.codigo = r.codigo"""
    )


def pga_por_periodo() -> pd.DataFrame:
    return consulta(
        """SELECT periodo_id, anio, numero,
                  ROUND(AVG(pga_periodo), 2)                                   AS pga_promedio,
                  COUNT(*)                                                     AS estudiantes,
                  ROUND(100.0 * AVG((estado_academico = 'En prueba académica')::int), 1) AS pct_prueba,
                  ROUND(100.0 * AVG((estado_academico = 'Condicional')::int), 1)         AS pct_condicional
           FROM academico.v_pga_periodo
           GROUP BY periodo_id, anio, numero
           ORDER BY anio, numero"""
    )


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------
def estadistica_cursos() -> pd.DataFrame:
    return consulta(
        """SELECT s.curso_id, s.curso, s.semestre_sugerido, s.creditos, s.intentos,
                  s.nota_promedio, s.tasa_reprobacion, s.cursos_que_bloquea,
                  c.componente, c.area
           FROM academico.v_estadistica_curso s
           JOIN academico.curso c USING (curso_id)
           ORDER BY s.semestre_sugerido, s.curso_id"""
    )


def reprobacion_curso_periodo() -> pd.DataFrame:
    return consulta(
        """SELECT i.curso_id, c.nombre AS curso, c.semestre_sugerido, i.periodo_id,
                  COUNT(*) AS evaluados,
                  ROUND(100.0 * COUNT(*) FILTER (WHERE i.estado = 'Reprobado') / COUNT(*), 1) AS tasa_reprobacion
           FROM academico.inscripcion i
           JOIN academico.curso c USING (curso_id)
           WHERE i.nota_final IS NOT NULL
           GROUP BY i.curso_id, c.nombre, c.semestre_sugerido, i.periodo_id"""
    )


def prerrequisitos() -> pd.DataFrame:
    return consulta(
        "SELECT curso_id, requisito_id, creditos_min, tipo FROM academico.prerrequisito"
    )


# ---------------------------------------------------------------------------
# Competencias digitales
# ---------------------------------------------------------------------------
def cumplimiento_rutas() -> pd.DataFrame:
    return consulta(
        """SELECT cd.ruta, cd.ruta_nombre,
                  COUNT(*)                                             AS estudiantes,
                  ROUND(100.0 * AVG(cd.cumplida::int), 1)              AS pct_cumplida,
                  ROUND(100.0 * AVG((cd.en_curso AND NOT cd.cumplida)::int), 1) AS pct_en_curso
           FROM academico.v_competencias_digitales cd
           JOIN academico.estudiante e ON e.codigo = cd.codigo
           WHERE e.condicion = 'Activo'
           GROUP BY cd.ruta, cd.ruta_nombre
           ORDER BY cd.ruta"""
    )


def rutas_por_estudiante() -> pd.DataFrame:
    return consulta(
        """SELECT cd.codigo, e.cohorte,
                  COUNT(*) FILTER (WHERE cd.cumplida) AS rutas_cumplidas
           FROM academico.v_competencias_digitales cd
           JOIN academico.estudiante e ON e.codigo = cd.codigo
           WHERE e.condicion = 'Activo'
           GROUP BY cd.codigo, e.cohorte"""
    )


def prueba_diagnostica() -> pd.DataFrame:
    return consulta(
        """SELECT p.puntaje, p.valida_curso, e.cohorte
           FROM academico.cd_prueba_diagnostica p
           JOIN academico.estudiante e ON e.codigo = p.codigo"""
    )


def cursos_cd() -> pd.DataFrame:
    return consulta(
        """SELECT cc.nombre, cc.ruta, cc.ruta_nombre, cc.vigente, ci.estado, COUNT(*) AS inscripciones
           FROM academico.cd_inscripcion ci
           JOIN academico.cd_curso cc USING (cd_curso_id)
           GROUP BY cc.nombre, cc.ruta, cc.ruta_nombre, cc.vigente, ci.estado"""
    )


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------
def conversaciones(limite: int = 20000) -> pd.DataFrame:
    """Bitácora sin texto libre (ni pregunta ni respuesta); el código del estudiante llega enmascarado."""
    return consulta(
        """SELECT log_id, session_id,
                  CASE WHEN codigo IS NULL THEN NULL
                       ELSE left(codigo, 3) || repeat('*', GREATEST(length(codigo) - 5, 0)) || right(codigo, 2) END
                    AS codigo_enmascarado,
                  canal, COALESCE(intencion, 'sin clasificar') AS intencion,
                  guardrail_flags, bloqueado, latencia_ms, calificacion, creado_en
           FROM chatbot.conversacion_log
           ORDER BY creado_en DESC
           LIMIT %s""",
        (limite,),
    )


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------
def corpus_rag() -> pd.DataFrame:
    # Nunca se selecciona la columna embedding (3072 dimensiones).
    return consulta(
        """SELECT COALESCE(metadata->>'fuente', metadata->>'source', 'Sin fuente')        AS fuente,
                  COALESCE(metadata->>'titulo', metadata->>'archivo', 'Sin título')       AS documento,
                  COALESCE(metadata->>'origen', metadata->>'blobType', '—')               AS origen,
                  length(text)                                                            AS caracteres
           FROM chatbot.rag_documentos"""
    )


# ---------------------------------------------------------------------------
# Noticias
# ---------------------------------------------------------------------------
def noticias() -> pd.DataFrame:
    return consulta(
        """SELECT noticia_id, titulo, url, fecha_pub, categoria, COALESCE(tipo, 'general') AS tipo,
                  left(resumen, 300) AS resumen, relevancia, scrapeado_en
           FROM chatbot.noticia
           ORDER BY fecha_pub DESC
           LIMIT 2000"""
    )


# ---------------------------------------------------------------------------
# Alertas tempranas (workflow 08 de n8n)
# ---------------------------------------------------------------------------
def alertas_tempranas() -> pd.DataFrame:
    """Alertas generadas por n8n; devuelve un DataFrame vacío si la tabla aún no existe."""
    import psycopg

    try:
        return consulta(
            """SELECT id, codigo, generada_en, fecha, nivel, estado, motivos, mensaje
               FROM chatbot.alerta_temprana
               ORDER BY generada_en DESC
               LIMIT 1000"""
        )
    except psycopg.errors.UndefinedTable:
        return pd.DataFrame()
