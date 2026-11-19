"""
Servidor MCP "chatbot-unab" (FastMCP · transporte Streamable HTTP · puerto 9000)

Expone herramientas relacionales sobre PostgreSQL/Supabase (simulación de
Banner/COSMOS) y el RAG institucional, para que agentes como n8n, Claude Desktop
u OpenAI las invoquen dinámicamente.

    POST http://<host>:9000/mcp      ← endpoint MCP (Authorization: Bearer <MCP_AUTH_TOKEN>)
    GET  http://<host>:9000/health   ← verificación de salud

Ejecutar:  python server.py            (o  docker compose up mcp-server)
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()

import planner  # noqa: E402
import rag  # noqa: E402
from db import normalizar_codigo, one, query  # noqa: E402

HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "9000"))
RIESGO_PATH = Path(__file__).with_name("modelo_riesgo.json")

mcp = FastMCP(
    "chatbot-unab",
    instructions=(
        "Herramientas del Chatbot de Apoyo Académico de Ingeniería de Sistemas (UNAB). "
        "Úsalas para consultar matrícula, avance del plan, proyección de grado, alertas, "
        "competencias digitales, calendario, noticias y documentos institucionales. "
        "Todas las herramientas de estudiante requieren el código estudiantil (U + 8 dígitos)."
    ),
    host=HOST,
    port=PORT,
    stateless_http=True,
    json_response=True,
)


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _periodo_actual() -> str:
    r = one("SELECT periodo_id FROM academico.periodo WHERE es_actual")
    return r["periodo_id"] if r else "2026-2"


def _resumen(codigo: str) -> dict:
    r = one("SELECT * FROM academico.v_estudiante_resumen WHERE codigo = %s", (codigo,))
    if not r:
        raise ValueError(f"No existe un estudiante con código {codigo} en el programa.")
    return r


def _cursos_catalogo(programa_id: str = "ISIS") -> dict[str, planner.Curso]:
    rows = query(
        """SELECT c.curso_id, c.nombre, c.creditos, c.semestre_sugerido,
                  COALESCE(array_agg(p.requisito_id) FILTER (WHERE p.tipo = 'prerrequisito'), '{}') AS prereqs,
                  COALESCE(MAX(p.creditos_min) FILTER (WHERE p.tipo = 'creditos'), 0)            AS cred_min,
                  COALESCE(s.tasa_reprobacion, 15) / 100.0                                         AS tasa_rep
           FROM academico.curso c
           LEFT JOIN academico.prerrequisito p USING (curso_id)
           LEFT JOIN academico.v_estadistica_curso s USING (curso_id)
           WHERE c.programa_id = %s
           GROUP BY c.curso_id, c.nombre, c.creditos, c.semestre_sugerido, s.tasa_reprobacion""",
        (programa_id,),
    )
    return {
        r["curso_id"]: planner.Curso(
            r["curso_id"], r["nombre"], r["creditos"], r["semestre_sugerido"],
            tuple(r["prereqs"]), int(r["cred_min"]), float(r["tasa_rep"]),
        )
        for r in rows
    }


ETIQUETAS_RIESGO = {
    "pga_acumulado": "PGA acumulado",
    "pga_ultimo_periodo": "PGA último periodo",
    "reprobados_por_periodo": "Reprobados por periodo",
    "creditos_por_periodo": "Ritmo de avance (créditos por periodo)",
    "trabaja": "Trabaja",
}


def _fmt_valor(k: str, v: float) -> str:
    if k == "trabaja":
        return "sí" if v >= 0.5 else "no"
    return f"{v:.1f}" if k == "creditos_por_periodo" else f"{v:.2f}"


def _frase_factor(f: dict) -> str:
    k, v, media = f["feature"], f["valor"], f["media"]
    if k == "trabaja":
        return f"{'trabajar' if v >= 0.5 else 'no trabajar'} mientras estudias"
    rel = "alto" if v > media else "bajo"
    return f"{f['etiqueta']} {rel} ({_fmt_valor(k, v)} vs {_fmt_valor(k, media)} del programa)"


def _explicacion_riesgo(factores: list[dict]) -> str:
    sube = next((f for f in factores if f["efecto"] == "aumenta"), None)
    baja = next((f for f in factores if f["efecto"] == "reduce"), None)
    partes = []
    if sube:
        partes.append(f"Lo que más eleva tu riesgo: {_frase_factor(sube)}")
    if baja:
        partes.append(f"Lo que más lo reduce: {_frase_factor(baja)}")
    return ". ".join(partes) + "." if partes else "Tus indicadores están en la media del programa."


def _riesgo_academico(r: dict) -> dict | None:
    """Probabilidad de quedar en prueba académica (modelo logístico entrenado en notebooks/).

    Además de `probabilidad` y `nivel`, devuelve la explicación del modelo (XAI): `factores`
    con la contribución de cada variable al log-odds (coef · z, z = (x − media) / desviación),
    ordenados por |contribución|, y una frase `explicacion`. Se cumple que
    intercepto + Σ contribuciones = logit(probabilidad).
    """
    if not RIESGO_PATH.exists() or r.get("pga_acumulado") is None:
        return None
    m = json.loads(RIESGO_PATH.read_text(encoding="utf-8"))
    periodos = max(1, r["periodos_cursados"] or 1)
    feats = {
        "pga_acumulado": float(r["pga_acumulado"]),
        "pga_ultimo_periodo": float(r["pga_ultimo_periodo"] or r["pga_acumulado"]),
        "reprobados_por_periodo": (r["total_reprobados"] or 0) / periodos,
        "creditos_por_periodo": (r["creditos_aprobados"] or 0) / periodos,
        "trabaja": 1.0 if r["trabaja"] else 0.0,
    }
    z = m["intercepto"]
    factores = []
    for k, coef in m["coeficientes"].items():
        x = (feats.get(k, 0.0) - m["medias"][k]) / m["desviaciones"][k]
        c = coef * x
        z += c
        factores.append({
            "feature": k,
            "etiqueta": ETIQUETAS_RIESGO.get(k, k),
            "valor": round(feats.get(k, 0.0), 2),
            "media": round(m["medias"][k], 2),
            "contribucion": round(c, 3),
            "efecto": "aumenta" if c > 0 else "reduce",
        })
    factores.sort(key=lambda f: abs(f["contribucion"]), reverse=True)
    import math

    p = 1 / (1 + math.exp(-z))
    nivel = "alto" if p >= 0.5 else "medio" if p >= 0.25 else "bajo"
    return {"probabilidad": round(p, 3), "nivel": nivel, "modelo": m.get("descripcion", "regresión logística"),
            "intercepto": round(m["intercepto"], 3), "factores": factores,
            "explicacion": _explicacion_riesgo(factores)}


# ---------------------------------------------------------------------------
# HERRAMIENTAS — Estado de matrícula y avance
# ---------------------------------------------------------------------------
@mcp.tool()
def consultar_estado_matricula(codigo: str) -> dict:
    """Estado de matrícula del periodo actual y resumen académico del estudiante.

    Devuelve nombre, semestre, créditos aprobados/pendientes, % de avance, PGA acumulado,
    estado académico (Normal / Condicional / En prueba académica, según art. 24 del
    Reglamento Estudiantil UNAB), estado de la matrícula y saldo pendiente.

    Args:
        codigo: Código estudiantil UNAB, p. ej. U00100001.
    """
    codigo = normalizar_codigo(codigo)
    r = _resumen(codigo)
    m = query(
        """SELECT m.periodo_id, m.estado, m.creditos_inscritos, m.valor_liquidado, m.valor_pagado
           FROM academico.matricula m JOIN academico.periodo p USING (periodo_id)
           WHERE m.codigo = %s ORDER BY p.anio DESC, p.numero DESC LIMIT 4""",
        (codigo,),
    )
    cursando = query(
        "SELECT curso_id, curso, creditos FROM academico.v_historial_academico WHERE codigo=%s AND estado='Cursando'",
        (codigo,),
    )
    return {"periodo_actual": _periodo_actual(), "resumen": r, "cursos_matriculados_actuales": cursando,
            "historial_matricula": m}


@mcp.tool()
def avance_plan_estudios(codigo: str) -> dict:
    """Avance del estudiante en el plan de estudios, semestre por semestre.

    Para cada semestre del plan indica cursos aprobados (con nota), en curso,
    reprobados pendientes y pendientes; además el porcentaje de avance por componente.

    Args:
        codigo: Código estudiantil UNAB.
    """
    codigo = normalizar_codigo(codigo)
    r = _resumen(codigo)
    filas = query(
        """SELECT semestre_sugerido, curso_id, curso, creditos, componente, estado, nota_aprobacion, veces_reprobado
           FROM academico.v_avance_plan WHERE codigo = %s ORDER BY semestre_sugerido, curso_id""",
        (codigo,),
    )
    por_sem: dict[int, dict] = {}
    for f in filas:
        s = por_sem.setdefault(f["semestre_sugerido"], {"semestre": f["semestre_sugerido"], "cursos": [],
                                                        "creditos_aprobados": 0, "creditos_totales": 0})
        s["cursos"].append({k: f[k] for k in ("curso_id", "curso", "creditos", "estado", "nota_aprobacion",
                                              "veces_reprobado")})
        s["creditos_totales"] += f["creditos"]
        if f["estado"] == "Aprobado":
            s["creditos_aprobados"] += f["creditos"]
    comp = query(
        """SELECT componente, SUM(creditos) FILTER (WHERE estado='Aprobado') AS aprobados, SUM(creditos) AS totales
           FROM academico.v_avance_plan WHERE codigo=%s GROUP BY componente ORDER BY componente""",
        (codigo,),
    )
    return {
        "estudiante": r["nombre_completo"],
        "creditos_aprobados": r["creditos_aprobados"],
        "creditos_totales": r["creditos_totales"],
        "porcentaje_avance": r["porcentaje_avance"],
        "semestres": list(por_sem.values()),
        "avance_por_componente": comp,
    }


@mcp.tool()
def historial_academico(codigo: str, periodo: str = "") -> dict:
    """Historial de calificaciones del estudiante y PGA por periodo.

    Args:
        codigo: Código estudiantil UNAB.
        periodo: (opcional) periodo específico, p. ej. '2025-2'. Si se omite, devuelve todos.
    """
    codigo = normalizar_codigo(codigo)
    sql = """SELECT periodo_id, curso_id, curso, creditos, nota_final, estado, intento
             FROM academico.v_historial_academico WHERE codigo=%s"""
    params: tuple = (codigo,)
    if periodo:
        sql += " AND periodo_id=%s"
        params += (periodo,)
    cursos = query(sql + " ORDER BY periodo_id, curso_id", params)
    pga = query(
        "SELECT periodo_id, pga_periodo, creditos_aprobados, cursos_reprobados, estado_academico "
        "FROM academico.v_pga_periodo WHERE codigo=%s ORDER BY anio, numero",
        (codigo,),
    )
    return {"cursos": cursos, "pga_por_periodo": pga}


@mcp.tool()
def cursos_habilitados(codigo: str, asumir_aprobados_actuales: bool = True) -> dict:
    """Cursos que el estudiante podrá inscribir el próximo periodo (prerrequisitos y créditos cumplidos).

    Por defecto asume que aprobará los cursos que está viendo ahora. Incluye la tasa histórica de
    reprobación y cuántos cursos bloquea cada uno, para planear una carga equilibrada.

    Args:
        codigo: Código estudiantil UNAB.
        asumir_aprobados_actuales: si es False, solo considera cursos ya aprobados.
    """
    codigo = normalizar_codigo(codigo)
    cursos = _cursos_catalogo()
    estados = ["Aprobado", "Homologado"] + (["Cursando"] if asumir_aprobados_actuales else [])
    hist = query("SELECT curso_id, estado FROM academico.inscripcion WHERE codigo=%s", (codigo,))
    aprob = {h["curso_id"] for h in hist if h["estado"] in estados}
    cursando = {h["curso_id"] for h in hist if h["estado"] == "Cursando"}
    reprob = {h["curso_id"] for h in hist if h["estado"] == "Reprobado"} - aprob
    creds = sum(cursos[c].creditos for c in aprob if c in cursos)
    stats = {r["curso_id"]: r for r in query(
        "SELECT curso_id, tasa_reprobacion, cursos_que_bloquea FROM academico.v_estadistica_curso")}
    out = []
    for c in cursos.values():
        if c.curso_id in aprob or (not asumir_aprobados_actuales and c.curso_id in cursando):
            continue
        if all(p in aprob for p in c.prereqs) and creds >= c.cred_min:
            out.append({"curso_id": c.curso_id, "curso": c.nombre, "creditos": c.creditos,
                        "semestre_sugerido": c.semestre, "es_repitencia": c.curso_id in reprob,
                        "tasa_reprobacion": stats[c.curso_id]["tasa_reprobacion"],
                        "cursos_que_bloquea": stats[c.curso_id]["cursos_que_bloquea"]})
    out.sort(key=lambda r: (not r["es_repitencia"], -r["cursos_que_bloquea"], r["semestre_sugerido"]))
    return {"supuesto": "Asume aprobados los cursos actuales." if asumir_aprobados_actuales else
            "Solo cursos ya aprobados.", "creditos_aprobados_considerados": creds,
            "cursos_habilitados": out, "total_creditos_disponibles": sum(r["creditos"] for r in out)}


@mcp.tool()
def proyeccion_graduacion(codigo: str, creditos_por_semestre: int = 18, incluir_cursos_actuales: bool = True) -> dict:
    """Proyección de semestres restantes hasta el grado.

    Calcula (1) un plan semestre a semestre que respeta prerrequisitos y el tope de créditos,
    priorizando la cadena crítica; y (2) una simulación Monte Carlo (400 escenarios) que usa el
    PGA del estudiante y la tasa histórica de reprobación de cada curso para estimar el periodo
    de grado probable (P50) y pesimista (P90).

    Args:
        codigo: Código estudiantil UNAB.
        creditos_por_semestre: carga máxima por semestre (12–20). Por defecto 18.
        incluir_cursos_actuales: asumir que aprobará los cursos que está cursando.
    """
    codigo = normalizar_codigo(codigo)
    creditos_por_semestre = max(10, min(20, int(creditos_por_semestre)))
    r = _resumen(codigo)
    cursos = _cursos_catalogo(r["programa_id"])
    estados = ("Aprobado", "Homologado", "Cursando") if incluir_cursos_actuales else ("Aprobado", "Homologado")
    aprob = {x["curso_id"] for x in query(
        "SELECT DISTINCT curso_id FROM academico.inscripcion WHERE codigo=%s AND estado = ANY(%s)",
        (codigo, list(estados)))}
    creds = sum(cursos[c].creditos for c in aprob if c in cursos)
    periodo = _periodo_actual()
    inicio = planner.siguiente_periodo(periodo, 1)

    plan = planner.planificar(cursos, aprob, creds, creditos_por_semestre)
    detalle = []
    for i, sem in enumerate(plan):
        detalle.append({
            "periodo": planner.siguiente_periodo(periodo, i + 1),
            "creditos": sum(cursos[c].creditos for c in sem),
            "cursos": [f"{cursos[c].nombre} ({cursos[c].creditos} cr)" for c in sem],
        })
    mc = planner.montecarlo(cursos, aprob, creds, r["pga_acumulado"], creditos_por_semestre)
    cc = planner.camino_critico({k: v for k, v in cursos.items() if k not in aprob})
    req_pend = [x["nombre"] for x in query(
        """SELECT rg.nombre FROM academico.estudiante_requisito er
           JOIN academico.requisito_grado rg USING (requisito_id)
           WHERE er.codigo=%s AND NOT er.cumplido AND er.requisito_id <> 'CD_RUTAS'""", (codigo,))]
    req_pend += [f"Ruta {x['ruta']} de Competencias Digitales ({x['ruta_nombre']})" for x in query(
        "SELECT ruta, ruta_nombre FROM academico.v_competencias_digitales WHERE codigo=%s AND NOT cumplida "
        "ORDER BY ruta", (codigo,))]
    return {
        "plan_completo": planner.plan_completo(cursos, aprob, plan),
        "requisitos_de_grado_pendientes": req_pend,
        "nota": "El periodo proyectado corresponde a TERMINAR LOS CURSOS del plan. Para graduarse también deben "
                "cumplirse los requisitos de grado pendientes listados.",
        "estudiante": r["nombre_completo"],
        "creditos_pendientes": r["creditos_totales"] - creds,
        "supuesto": f"Carga máxima {creditos_por_semestre} créditos/semestre; "
                    + ("asume aprobar los cursos actuales." if incluir_cursos_actuales else "sin contar cursos actuales."),
        "semestres_restantes_ideal": len(plan),
        "periodo_grado_ideal": detalle[-1]["periodo"] if detalle else periodo,
        "cadena_critica_semestres": max(cc.values(), default=0),
        "plan_sugerido": detalle,
        "proyeccion_probabilistica": {
            **mc,
            "periodo_grado_p50": planner.siguiente_periodo(periodo, mc["semestres_p50"]),
            "periodo_grado_p90": planner.siguiente_periodo(periodo, mc["semestres_p90"]),
            "metodo": "Monte Carlo, 400 simulaciones, p(aprobar)=σ(logit(1−tasa_rep)+1.9·(PGA−3.55))",
        },
        "inicio_proyeccion": inicio,
    }


@mcp.tool()
def alertas_requisitos(codigo: str) -> dict:
    """Alertas priorizadas: estado académico de riesgo, matrícula pendiente, cursos cuello de botella,
    rutas de competencias digitales incompletas, requisitos de grado y habilitación de práctica.

    Args:
        codigo: Código estudiantil UNAB.
    """
    codigo = normalizar_codigo(codigo)
    rows = query(
        """SELECT prioridad, tipo, mensaje FROM academico.v_alertas WHERE codigo=%s
           ORDER BY CASE prioridad WHEN 'ALTA' THEN 1 WHEN 'MEDIA' THEN 2 WHEN 'BAJA' THEN 3 ELSE 4 END""",
        (codigo,),
    )
    req = query(
        """SELECT rg.nombre, er.cumplido, er.detalle FROM academico.estudiante_requisito er
           JOIN academico.requisito_grado rg USING (requisito_id)
           WHERE er.codigo=%s AND er.requisito_id <> 'CD_RUTAS'""",
        (codigo,),
    )
    return {"alertas": rows, "total": len(rows), "requisitos_de_grado": req}


@mcp.tool()
def competencias_digitales(codigo: str) -> dict:
    """Estado del estudiante en la Ruta de Competencias Digitales del CCD (requisito de grado):
    Ruta 1 Competencias Digitales Básicas (Interacción Digital), Ruta 2 Analítica y Contenido Digital,
    Ruta 3 Tecnología Transformativa. Incluye prueba diagnóstica, cursos tomados (incluida la oferta
    anterior a 2026 homologada) y la oferta disponible para las rutas pendientes.

    Args:
        codigo: Código estudiantil UNAB.
    """
    codigo = normalizar_codigo(codigo)
    rutas = query(
        "SELECT ruta, ruta_nombre, cumplida, en_curso, detalle FROM academico.v_competencias_digitales "
        "WHERE codigo=%s ORDER BY ruta", (codigo,))
    prueba = one("SELECT fecha, puntaje, valida_curso FROM academico.cd_prueba_diagnostica WHERE codigo=%s", (codigo,))
    pendientes = [r["ruta"] for r in rutas if not r["cumplida"] and not r["en_curso"]]
    oferta = query(
        "SELECT ruta, nombre, horas, modalidad, descripcion FROM academico.cd_curso WHERE vigente AND ruta = ANY(%s) "
        "ORDER BY ruta, nombre", (pendientes,)) if pendientes else []
    return {
        "rutas": rutas,
        "rutas_cumplidas": sum(1 for r in rutas if r["cumplida"]),
        "insignia_lista": all(r["cumplida"] for r in rutas),
        "prueba_diagnostica": prueba,
        "oferta_para_rutas_pendientes": oferta,
        "nota": "Al graduarse, quien completa las 3 rutas recibe la insignia digital de competencias digitales.",
    }


@mcp.tool()
def recomendaciones_personalizadas(codigo: str) -> dict:
    """Recomendaciones personalizadas para el éxito académico basadas en datos.

    Combina: estado académico, riesgo estimado por un modelo de regresión logística (probabilidad de
    quedar en prueba académica), carga recomendada, cursos difíciles habilitados (tasa histórica de
    reprobación), cuellos de botella y competencias digitales.

    Args:
        codigo: Código estudiantil UNAB.
    """
    codigo = normalizar_codigo(codigo)
    r = _resumen(codigo)
    recs: list[dict] = []
    riesgo = _riesgo_academico(r)

    # Carga recomendada
    if r["estado_academico"] == "En prueba académica":
        carga = "12–14"
        recs.append({"tema": "Estado académico", "recomendacion":
                     "Estás en prueba académica: inscribe máximo 14 créditos, prioriza las repitencias y "
                     "solicita acompañamiento en el programa de Éxito Estudiantil y tutorías de pares."})
    elif r["estado_academico"] == "Condicional" or (riesgo and riesgo["nivel"] == "alto"):
        carga = "14–16"
        recs.append({"tema": "Estado académico", "recomendacion":
                     "Tu PGA está cerca del límite de 3.20. Equilibra la carga y reserva horas semanales de "
                     "estudio para los cursos con mayor reprobación."})
    elif r["trabaja"]:
        carga = "12–15"
        recs.append({"tema": "Trabajo y estudio", "recomendacion":
                     "Como trabajas, una carga de 12–15 créditos reduce el riesgo de reprobar."})
    else:
        carga = "16–20" if (r["pga_acumulado"] or 0) >= 4.0 else "16–18"

    # Cursos difíciles habilitados
    dif = query(
        """SELECT h.curso, s.tasa_reprobacion FROM academico.v_cursos_habilitados h
           JOIN academico.v_estadistica_curso s USING (curso_id)
           WHERE h.codigo=%s AND s.tasa_reprobacion >= 25 ORDER BY s.tasa_reprobacion DESC LIMIT 3""", (codigo,))
    if len(dif) >= 2:
        recs.append({"tema": "Equilibrio de carga", "recomendacion":
                     "Evita inscribir juntos " + " y ".join(f"{d['curso']} ({d['tasa_reprobacion']}% reprobación)"
                                                           for d in dif[:2]) + "; combínalos con cursos más livianos."})
    elif dif:
        recs.append({"tema": "Curso exigente", "recomendacion":
                     f"{dif[0]['curso']} tiene {dif[0]['tasa_reprobacion']}% de reprobación histórica: "
                     "asiste a monitorías desde la primera semana."})

    # Cuellos de botella
    for a in query("SELECT mensaje FROM academico.v_alertas WHERE codigo=%s AND tipo='Cuello de botella' LIMIT 2",
                   (codigo,)):
        recs.append({"tema": "Prerrequisitos", "recomendacion": a["mensaje"]})

    # Competencias digitales
    cd = query("SELECT ruta, ruta_nombre FROM academico.v_competencias_digitales "
               "WHERE codigo=%s AND NOT cumplida AND NOT en_curso ORDER BY ruta", (codigo,))
    sugerencia = {1: "Interacción Digital", 2: "Habilidades de Analítica Digital (útil para Ciencia de Datos)",
                  3: "IA Generativa (alineada con Inteligencia Artificial y Aprendizaje Automático)"}
    for c in cd:
        recs.append({"tema": "Competencias digitales", "recomendacion":
                     f"Completa la Ruta {c['ruta']} ({c['ruta_nombre']}); para Ingeniería de Sistemas sugerimos "
                     f"{sugerencia[c['ruta']]}. Inscripción en COSMOS por ciclos mensuales o vacacionales."})

    # Fortalezas
    top = query("""SELECT curso, nota_final FROM academico.v_historial_academico
                   WHERE codigo=%s AND estado='Aprobado' ORDER BY nota_final DESC LIMIT 3""", (codigo,))
    if top and top[0]["nota_final"] and top[0]["nota_final"] >= 4.3:
        recs.append({"tema": "Fortalezas", "recomendacion":
                     "Destacas en " + ", ".join(t["curso"] for t in top) +
                     ". Considera monitorías, semilleros de investigación o electivas en esa línea."})
    if (r["creditos_aprobados"] or 0) >= 100:
        recs.append({"tema": "Grado", "recomendacion":
                     "Empieza a preparar la práctica profesional y la inscripción a Saber Pro; revisa la "
                     "suficiencia de inglés B1."})
    return {"estudiante": r["nombre_completo"], "estado_academico": r["estado_academico"],
            "pga_acumulado": r["pga_acumulado"], "carga_recomendada_creditos": carga,
            "riesgo_academico": riesgo, "recomendaciones": recs}


# ---------------------------------------------------------------------------
# HERRAMIENTAS — Información institucional
# ---------------------------------------------------------------------------
@mcp.tool()
def info_curso(nombre_o_codigo: str) -> dict:
    """Información de un curso del plan: créditos, semestre, prerrequisitos, cursos que habilita y
    estadísticas históricas (nota promedio, tasa de reprobación).

    Args:
        nombre_o_codigo: código (ISIS2303) o parte del nombre ("estructuras de datos").
    """
    q = nombre_o_codigo.strip()
    c = one("""SELECT c.*, s.nota_promedio, s.tasa_reprobacion, s.cursos_que_bloquea
               FROM academico.curso c JOIN academico.v_estadistica_curso s USING (curso_id)
               WHERE c.curso_id ILIKE %s OR unaccent_lower(c.nombre) LIKE '%%' || unaccent_lower(%s) || '%%'
               ORDER BY (c.curso_id ILIKE %s) DESC LIMIT 1""", (q, q, q))
    if not c:
        return {"error": f"No encontré un curso que coincida con '{q}'."}
    pre = query("""SELECT COALESCE(r.nombre, 'Mínimo ' || p.creditos_min || ' créditos aprobados') AS requisito
                   FROM academico.prerrequisito p LEFT JOIN academico.curso r ON r.curso_id = p.requisito_id
                   WHERE p.curso_id=%s""", (c["curso_id"],))
    hab = query("""SELECT c2.nombre FROM academico.prerrequisito p JOIN academico.curso c2 ON c2.curso_id=p.curso_id
                   WHERE p.requisito_id=%s""", (c["curso_id"],))
    c.pop("dificultad", None)
    return {**c, "prerrequisitos": [p["requisito"] for p in pre], "habilita": [h["nombre"] for h in hab]}


@mcp.tool()
def buscar_documentos_institucionales(pregunta: str, k: int = 5) -> dict:
    """Búsqueda RAG híbrida (semántica pgvector + léxica) en documentos institucionales: Reglamento
    Estudiantil de Pregrado, Centro de Competencias Digitales (rutas, prueba diagnóstica, insignia),
    información del programa y noticias. Devuelve fragmentos con su fuente para citar.

    Args:
        pregunta: pregunta en lenguaje natural.
        k: número de fragmentos (1–8).
    """
    k = max(1, min(8, int(k)))
    t0 = time.time()
    res = rag.buscar(pregunta, k)
    return {"pregunta": pregunta, "fragmentos": res, "latencia_ms": int((time.time() - t0) * 1000),
            "instruccion": "Responde SOLO con base en estos fragmentos y cita la fuente."}


@mcp.tool()
def calendario_academico(categoria: str = "", solo_proximos: bool = True) -> dict:
    """Fechas del calendario académico: inscripciones, pruebas diagnósticas, inicio de cursos,
    matrícula, cancelaciones, exámenes, cursos vacacionales y grados. Fuente: Google Sheets
    (con respaldo en la base de datos).

    Args:
        categoria: (opcional) filtra por categoría o palabra clave, p. ej. "Inscripciones", "Prueba diagnóstica".
        solo_proximos: si es True, solo eventos que no han terminado.
    """
    eventos, fuente = [], "Google Sheets"
    url = os.environ.get("CALENDAR_SHEET_CSV_URL")
    try:
        if not url:
            raise RuntimeError("sin URL")
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        eventos = list(csv.DictReader(io.StringIO(resp.text)))
    except Exception:
        fuente = "Base de datos (respaldo)"
        eventos = query("SELECT periodo_id AS periodo, categoria, evento, fecha_inicio, fecha_fin, publico, fuente "
                        "FROM chatbot.calendario ORDER BY fecha_inicio")
    hoy = date.today().isoformat()
    out = []
    for e in eventos:
        fin = e.get("fecha_fin") or e.get("fecha_inicio")
        if solo_proximos and fin and str(fin) < hoy:
            continue
        if categoria and categoria.lower() not in (str(e.get("categoria", "")) + " " + str(e.get("evento", ""))).lower():
            continue
        out.append(e)
    return {"hoy": hoy, "fuente": fuente, "eventos": out[:25]}


@mcp.tool()
def noticias_recientes(tema: str = "", limite: int = 5) -> dict:
    """Noticias, convocatorias, nuevos cursos y certificaciones de la UNAB obtenidas por el scraper
    periódico del sitio institucional.

    Args:
        tema: (opcional) palabra clave, p. ej. "competencias digitales", "convocatoria", "inteligencia artificial".
        limite: número de noticias (1–10).
    """
    limite = max(1, min(10, int(limite)))
    if tema:
        rows = query("""SELECT titulo, url, fecha_pub, tipo, resumen FROM chatbot.noticia
                        WHERE to_tsvector('spanish', titulo || ' ' || coalesce(resumen,'')) @@ plainto_tsquery('spanish', %s)
                           OR titulo ILIKE '%%' || %s || '%%'
                        ORDER BY fecha_pub DESC LIMIT %s""", (tema, tema, limite))
    else:
        rows = query("SELECT titulo, url, fecha_pub, tipo, resumen FROM chatbot.noticia "
                     "ORDER BY relevancia DESC NULLS LAST, fecha_pub DESC LIMIT %s", (limite,))
    return {"noticias": rows, "total": len(rows)}


@mcp.resource("unab://plan-de-estudios")
def recurso_plan() -> str:
    """Plan de estudios completo de Ingeniería de Sistemas en JSON."""
    return json.dumps(query("SELECT curso_id, nombre, creditos, semestre_sugerido, componente FROM academico.curso "
                            "ORDER BY semestre_sugerido, curso_id"), ensure_ascii=False)


@mcp.prompt()
def asesor_academico(codigo: str) -> str:
    """Prompt para generar un informe de consejería académica completo."""
    return (f"Actúa como consejero académico de Ingeniería de Sistemas UNAB. Para el estudiante {codigo}: "
            "1) consulta su estado de matrícula, 2) su avance, 3) alertas, 4) proyección de grado y "
            "5) recomendaciones. Redacta un informe breve, empático y accionable en español.")


# ---------------------------------------------------------------------------
# HTTP: salud + autenticación Bearer
# ---------------------------------------------------------------------------
@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    try:
        one("SELECT 1 AS ok")
        db_ok = True
    except Exception:
        db_ok = False
    return JSONResponse({"status": "ok" if db_ok else "degraded", "db": db_ok, "server": "chatbot-unab"})


HERRAMIENTAS_REST = {  # solo herramientas SIN datos de estudiantes (esas exigen PIN: /api/login, /api/dashboard)
    "info_curso", "buscar_documentos_institucionales", "calendario_academico", "noticias_recientes",
}


@mcp.custom_route("/api/tool/{nombre}", methods=["POST"])
async def api_tool(request: Request) -> JSONResponse:
    """Puente REST (usado por el dashboard de la app vía n8n): POST JSON con los argumentos de la herramienta."""
    import anyio

    nombre = request.path_params["nombre"]
    if nombre not in HERRAMIENTAS_REST:
        return JSONResponse({"error": f"herramienta desconocida: {nombre}"}, status_code=404)
    try:
        args = await request.json()
    except Exception:
        args = {}
    try:
        fn = globals()[nombre]
        res = await anyio.to_thread.run_sync(lambda: fn(**args))
        return JSONResponse(json.loads(json.dumps(res, default=str)))
    except (ValueError, TypeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


def _pin_valido(codigo: str, pin: str) -> bool:
    r = one("SELECT academico.verificar_pin(%s, %s) AS ok", (codigo, str(pin or "")))
    return bool(r and r["ok"])


@mcp.custom_route("/api/login", methods=["POST"])
async def api_login(request: Request) -> JSONResponse:
    """Valida código + PIN del estudiante (usado por n8n antes de atender al chat o a la app)."""
    import anyio

    try:
        body = await request.json()
        codigo = normalizar_codigo(body.get("codigo", ""))
    except Exception:
        return JSONResponse({"ok": False, "mensaje": "Código estudiantil inválido (formato U00123456)."})

    def _run():
        if not _pin_valido(codigo, body.get("pin", "")):
            return {"ok": False, "mensaje": "Código o PIN incorrectos."}
        r = _resumen(codigo)
        return {"ok": True, "estudiante": {k: r[k] for k in ("codigo", "nombre_completo", "programa", "cohorte")}}

    try:
        return JSONResponse(await anyio.to_thread.run_sync(_run))
    except ValueError as exc:
        return JSONResponse({"ok": False, "mensaje": str(exc)})


@mcp.custom_route("/api/dashboard", methods=["POST"])
async def api_dashboard(request: Request) -> JSONResponse:
    """Tablero completo del estudiante para la app móvil (una sola llamada)."""
    import anyio

    try:
        body = await request.json()
        codigo = normalizar_codigo(body.get("codigo", ""))
    except Exception:
        return JSONResponse({"ok": False, "mensaje": "Código estudiantil inválido."})

    def _run():
        if not _pin_valido(codigo, body.get("pin", "")):
            return {"ok": False, "mensaje": "Código o PIN incorrectos."}
        resumen = _resumen(codigo)
        try:
            proy = proyeccion_graduacion(codigo)
        except Exception:
            proy = None
        return {
            "ok": True,
            "resumen": resumen,
            "alertas": alertas_requisitos(codigo)["alertas"],
            "competencias": competencias_digitales(codigo)["rutas"],
            "avance": avance_plan_estudios(codigo)["semestres"],
            "proyeccion": proy,
            "riesgo": _riesgo_academico(resumen),
            "historial_pga": query(
                "SELECT periodo_id, pga_periodo, estado_academico, creditos_aprobados "
                "FROM academico.v_pga_periodo WHERE codigo=%s ORDER BY anio, numero", (codigo,)),
            "noticias": noticias_recientes(None, 8)["noticias"],
            "calendario": calendario_academico(None, True)["eventos"][:12],
        }

    res = await anyio.to_thread.run_sync(_run)
    return JSONResponse(json.loads(json.dumps(res, default=str)))


def build_app():
    import hmac

    from starlette.middleware.base import BaseHTTPMiddleware

    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        raise RuntimeError("Falta MCP_AUTH_TOKEN: el servidor no arranca sin autenticación (fail-closed).")
    esperado = f"Bearer {token}".encode()
    app = mcp.streamable_http_app()

    class BearerAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path.startswith(("/mcp", "/api")):
                auth = request.headers.get("authorization", "").encode()
                if not hmac.compare_digest(auth, esperado):
                    return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)

    app.add_middleware(BearerAuth)
    return app


if __name__ == "__main__":
    import sys

    if "--stdio" in sys.argv:  # para Claude Desktop local
        mcp.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(build_app(), host=HOST, port=PORT, log_level="info")
