"""
Ruta de autoaprendizaje personalizada (lógica pura, sin red ni base de datos).

`armar_ruta()` recibe el perfil del estudiante y el estado de cada curso del plan (lo arma
`server.ruta_autoaprendizaje` con las vistas académicas) y devuelve un plan semanal determinista:

1. Prioriza 2–4 cursos foco: cursos que está viendo, repitencias, cursos con mayor probabilidad
   de reprobar (tasa histórica ajustada por su PGA, `planner.prob_aprobar`), cursos que bloquean
   la cadena de prerrequisitos y bases aprobadas con nota baja que habilitan cursos pendientes.
2. Calcula las horas semanales de estudio autónomo según el riesgo del modelo, el estado
   académico, la carga actual y si trabaja; las reparte entre los cursos foco.
3. Asigna recursos abiertos verificados (recursos_aprendizaje.json) y estrategias de aprendizaje
   autorregulado con respaldo empírico, organizadas en el ciclo de Zimmerman
   (planificación → ejecución y monitoreo → autorreflexión), con hitos de autoevaluación.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from planner import prob_aprobar

CATALOGO_PATH = Path(__file__).with_name("recursos_aprendizaje.json")
NOTA_REFUERZO = 3.5  # aprobada por debajo de esta nota → candidata a "refuerzo de base"

ESTRATEGIAS = [
    {"id": "recuperacion", "nombre": "Práctica de recuperación",
     "como": "Cierra cada sesión respondiendo de memoria, sin apuntes: 3 ideas clave o 2–3 ejercicios. "
             "Recordar fortalece más que releer o subrayar.",
     "evidencia": "Roediger y Karpicke (2006); Dunlosky et al. (2013): utilidad alta."},
    {"id": "espaciada", "nombre": "Práctica espaciada",
     "como": "Reparte el estudio en varias sesiones cortas por semana y repasa lo de 1 y 3 semanas atrás, "
             "en lugar de concentrarlo la víspera del parcial.",
     "evidencia": "Cepeda et al. (2006); Dunlosky et al. (2013): utilidad alta."},
    {"id": "intercalado", "nombre": "Intercalado",
     "como": "Mezcla tipos de ejercicio y temas en una misma sesión para aprender a elegir el método, "
             "no solo a aplicarlo.",
     "evidencia": "Rohrer y Taylor (2007); Dunlosky et al. (2013): utilidad moderada, alta en matemáticas."},
    {"id": "autoexplicacion", "nombre": "Autoexplicación",
     "como": "Al resolver o leer, explica en voz alta o por escrito por qué cada paso es correcto y cómo se "
             "conecta con lo que ya sabes.",
     "evidencia": "Chi et al. (1994); Dunlosky et al. (2013): utilidad moderada."},
    {"id": "zimmerman", "nombre": "Ciclo de autorregulación (Zimmerman)",
     "como": "Planifica (metas y agenda), monitorea (horas reales y confianza por curso cada semana) y "
             "evalúa (compara resultados con tus metas y ajusta la estrategia).",
     "evidencia": "Zimmerman (2002), modelo cíclico del aprendizaje autorregulado."},
]

ACTIVIDADES = [
    "Estudia el tema de la semana con «{r}» y cierra con 3 ideas clave escritas de memoria (recuperación).",
    "Resuelve ejercicios mezclando temas de semanas anteriores (intercalado) y explica cada paso (autoexplicación).",
    "Haz un mini-quiz sin apuntes de lo visto; marca errores y vuelve a «{r}» solo en esos puntos (recuperación).",
]

CONSEJOS_FACTOR = {
    "reprobados_por_periodo": "Has reprobado cursos en periodos anteriores: no te saltes el mini-quiz semanal; "
                              "detectar pronto lo que no dominas es la mejor protección.",
    "pga_ultimo_periodo": "Tu último periodo bajó respecto a la media: fija una meta de nota por curso foco y "
                          "revísala cada semana.",
    "pga_acumulado": "Tu PGA acumulado está por debajo de la media del programa: combina esta ruta con "
                     "tutorías desde la primera semana, no después del primer parcial.",
    "trabaja": "Como trabajas: agenda bloques fijos de 25–40 min en días laborales y una sesión larga el fin de "
               "semana; los bloques cortos y espaciados rinden más que una maratón.",
    "creditos_por_periodo": "Tu ritmo de avance es bajo: dar prioridad a los cursos que bloquean otros acorta tu "
                            "camino al grado.",
}


@lru_cache(maxsize=1)
def cargar_catalogo(path: str | None = None) -> dict:
    return json.loads(Path(path or CATALOGO_PATH).read_text(encoding="utf-8"))


def recursos_para(curso_id: str, area: str, catalogo: dict, maximo: int = 4) -> list[dict]:
    ids = catalogo.get("cursos", {}).get(curso_id) or catalogo.get("areas", {}).get(area) or []
    rec = catalogo.get("recursos", {})
    return [{"id": i, **rec[i]} for i in ids if i in rec][:maximo]


# ---------------------------------------------------------------------------
# 1. Priorización
# ---------------------------------------------------------------------------
def priorizar_cursos(cursos: list[dict], pga: float | None) -> list[dict]:
    """Puntúa los cursos candidatos y devuelve la lista ordenada (mayor prioridad primero).

    Cada curso: curso_id, curso, area, estado ('Aprobado' | 'Cursando' | 'Reprobado (pendiente)' |
    'Pendiente'), habilitado (bool, puede inscribirlo el próximo periodo), nota_aprobacion,
    veces_reprobado, tasa_reprobacion (0–100), cursos_que_bloquea, prereqs (lista de curso_id).
    """
    no_aprobados = {c["curso_id"] for c in cursos if c["estado"] != "Aprobado"}
    dependientes: dict[str, int] = {}
    for c in cursos:
        if c["curso_id"] in no_aprobados:
            for p in c.get("prereqs") or ():
                dependientes[p] = dependientes.get(p, 0) + 1

    out = []
    for c in cursos:
        estado, rep = c["estado"], int(c.get("veces_reprobado") or 0)
        tasa = float(c.get("tasa_reprobacion") or 15) / 100
        bloquea = int(c.get("cursos_que_bloquea") or 0)
        motivos: list[str] = []
        if estado == "Cursando":
            score, tipo = 3.0, "cursando"
            motivos.append("lo estás cursando este periodo")
        elif estado == "Reprobado (pendiente)" and c.get("habilitado"):
            score, tipo = 2.0, "repitencia"
        elif estado == "Pendiente" and c.get("habilitado"):
            score, tipo = 1.0, "preparacion"
            motivos.append("podrás inscribirlo el próximo periodo")
        elif estado == "Aprobado" and c.get("nota_aprobacion") is not None \
                and float(c["nota_aprobacion"]) < NOTA_REFUERZO and dependientes.get(c["curso_id"]):
            nota = float(c["nota_aprobacion"])
            n = dependientes[c["curso_id"]]
            score, tipo = 1.0 + (NOTA_REFUERZO - nota) * 3, "refuerzo"
            motivos.append(f"lo aprobaste con {nota:.1f} y es prerrequisito de {n} curso(s) pendiente(s)")
            out.append({**c, "puntaje": round(score + 0.3 * min(bloquea, 5), 2), "tipo": tipo,
                        "prob_reprobar": None, "motivos": motivos})
            continue
        else:
            continue
        if rep:
            score += 2.5
            tipo = "repitencia"
            motivos.insert(0, f"lo has reprobado {rep} " + ("vez" if rep == 1 else "veces"))
        p_rep = 1 - prob_aprobar(pga, tasa)
        score += 4 * p_rep
        if p_rep >= 0.25:
            motivos.append(f"riesgo de reprobar estimado {round(p_rep * 100)}% (tasa histórica {round(tasa * 100)}%)")
        if bloquea >= 3:
            score += 0.3 * min(bloquea, 5)
            motivos.append(f"bloquea {bloquea} cursos posteriores")
        out.append({**c, "puntaje": round(score, 2), "tipo": tipo, "prob_reprobar": round(p_rep, 3),
                    "motivos": motivos})
    out.sort(key=lambda c: (-c["puntaje"], c.get("semestre_sugerido") or 99, c["curso_id"]))
    return out


# ---------------------------------------------------------------------------
# 2. Horas y reparto
# ---------------------------------------------------------------------------
def horas_semanales(perfil: dict) -> int:
    """Horas semanales de estudio autónomo ADICIONAL para la ruta (4–12)."""
    nivel = (perfil.get("riesgo") or {}).get("nivel")
    h = {"bajo": 5, "medio": 7, "alto": 9}.get(nivel, 6)
    estado = perfil.get("estado_academico") or ""
    if estado == "En prueba académica":
        h += 2
    elif estado == "Condicional":
        h += 1
    if perfil.get("trabaja"):
        h -= 2
    if (perfil.get("creditos_en_curso") or 0) >= 18:
        h -= 1
    return max(4, min(12, h))


def numero_cursos_foco(horas: int, candidatos: int) -> int:
    n = 2 if horas <= 5 else 3 if horas <= 8 else 4
    return min(n, candidatos)


def repartir_horas(horas: int, puntajes: list[float]) -> list[float]:
    """Reparte proporcional al puntaje, mínimo 1 h por curso, en múltiplos de 0.5 h."""
    if not puntajes:
        return []
    tot = sum(puntajes) or 1
    out = [max(1.0, round(horas * p / tot * 2) / 2) for p in puntajes]
    # ajuste fino para que la suma sea exactamente `horas`
    i = 0
    while sum(out) != horas and i < 100:
        j = out.index(max(out)) if sum(out) > horas else out.index(min(out))
        out[j] += -0.5 if sum(out) > horas else 0.5
        out[j] = max(1.0, out[j])
        i += 1
    return out


# ---------------------------------------------------------------------------
# 3. Plan
# ---------------------------------------------------------------------------
def _objetivo(c: dict) -> str:
    nombre = c["curso"]
    if c["tipo"] == "repitencia":
        return (f"Cerrar las brechas que llevaron a reprobar {nombre}: identifica los temas con más errores y "
                "domínalos antes del primer parcial.")
    if c["tipo"] == "refuerzo":
        return f"Reforzar las bases de {nombre} para llegar con seguridad a los cursos que habilita."
    if c["tipo"] == "preparacion":
        return f"Adelantar los fundamentos de {nombre} para inscribirlo el próximo periodo con ventaja."
    return f"Aprobar {nombre} con 3.5 o más, al día semana a semana y sin estudiar a última hora."


def hitos_autoevaluacion(semanas: int) -> dict[int, str]:
    mitad = max(2, semanas // 2)
    h = {1: "Diagnóstico: autoevalúate sin apuntes en cada curso foco (0–5) y fija una meta de nota concreta."}
    if semanas >= 10:
        h[max(2, semanas // 4)] = "Control: mini-quiz cronometrado por curso; compara con tu diagnóstico."
        h[semanas * 3 // 4] = "Control: mini-quiz cronometrado por curso; compara con el de mitad de ruta."
    h[mitad] = ("Mitad de ruta: simulacro tipo parcial; si en un curso no llegas a 3.5, agenda tutoría esta "
                "misma semana y ajusta las horas.")
    h[semanas] = ("Cierre: simulacro final y autorreflexión: ¿cumpliste tu meta?, ¿qué estrategia funcionó?, "
                  "¿qué ajustas para el próximo ciclo?")
    return h


def _repaso(w: int) -> str | None:
    if w < 2:
        return None
    previas = [str(w - 1)] + ([str(w - 3)] if w >= 4 else [])
    return f"Repaso espaciado (15–20 min por curso) de lo estudiado en la semana {' y '.join(previas)}."


def plan_semanal(foco: list[dict], semanas: int) -> list[dict]:
    hitos = hitos_autoevaluacion(semanas)
    plan = []
    for w in range(1, semanas + 1):
        fase = "Planificación" if w == 1 else "Autorreflexión" if w == semanas else "Ejecución y monitoreo"
        sesiones = []
        for k, c in enumerate(foco):
            recs = c["recursos"]
            r = recs[((w - 1) * len(recs)) // semanas] if recs else None
            if w == 1:
                act = (f"Revisa el programa de {c['curso']}, haz el diagnóstico y explora «{r['titulo']}»."
                       if r else f"Revisa el programa de {c['curso']} y haz el diagnóstico.")
            else:
                act = ACTIVIDADES[(w + k) % len(ACTIVIDADES)].format(r=r["titulo"] if r else "tus apuntes")
            sesiones.append({"curso_id": c["curso_id"], "curso": c["curso"], "horas": c["horas_semana"],
                             "actividad": act,
                             "recurso": {"titulo": r["titulo"], "url": r["url"]} if r else None})
        semana = {"semana": w, "fase": fase, "sesiones": sesiones,
                  "monitoreo": "Registra horas reales vs. planeadas y tu confianza (1–5) en cada curso foco."}
        if w == 1:
            semana["objetivos"] = [c["objetivo"] for c in foco]
        if len(foco) > 1 and 1 < w < semanas:
            semana["intercalado"] = "Alterna cursos en una misma jornada en lugar de dedicar un día entero a uno."
        rep = _repaso(w)
        if rep:
            semana["repaso"] = rep
        if w in hitos:
            semana["autoevaluacion"] = hitos[w]
        plan.append(semana)
    return plan


def consejos_perfil(riesgo: dict | None) -> list[str]:
    if not riesgo:
        return []
    out = []
    for f in riesgo.get("factores") or []:
        if f.get("efecto") == "aumenta" and f.get("feature") in CONSEJOS_FACTOR:
            out.append(CONSEJOS_FACTOR[f["feature"]])
        if len(out) == 2:
            break
    return out


def servicios_apoyo(perfil: dict, foco: list[dict], cd_pendientes: list[dict]) -> list[dict]:
    estado = perfil.get("estado_academico") or ""
    nivel = (perfil.get("riesgo") or {}).get("nivel")
    s = []
    if estado in ("En prueba académica", "Condicional") or nivel == "alto" or any(c["tipo"] == "repitencia" for c in foco):
        s.append({"servicio": "Programa de Éxito Estudiantil",
                  "para": "Acompañamiento académico y tutorías de pares para los cursos foco."})
    basicas = [c["curso"] for c in foco if c.get("area") in ("Matemáticas", "Física")]
    s.append({"servicio": "Monitorías académicas",
              "para": ("Resolver dudas de " + ", ".join(basicas) + " con monitores de ciencias básicas."
                       if basicas else "Resolver dudas semanales de los cursos foco con monitores del programa.")})
    if perfil.get("trabaja") or nivel in ("medio", "alto"):
        s.append({"servicio": "Bienestar Universitario",
                  "para": "Orientación en hábitos de estudio, manejo del tiempo y del estrés."})
    s.append({"servicio": "Biblioteca UNAB", "para": "Bases de datos académicas, préstamo de textos y salas de estudio."})
    if cd_pendientes:
        rutas = ", ".join(f"Ruta {r['ruta']} ({r['ruta_nombre']})" for r in cd_pendientes)
        s.append({"servicio": "Centro de Competencias Digitales",
                  "para": f"Pendiente(s): {rutas}. Es requisito de grado; inscríbete en COSMOS."})
    return s


def armar_ruta(perfil: dict, cursos: list[dict], catalogo: dict, semanas: int = 8,
               cd_pendientes: list[dict] | None = None) -> dict:
    """Arma la ruta completa. `perfil`: nombre, estado_academico, pga_acumulado, trabaja,
    creditos_en_curso, riesgo (salida de server._riesgo_academico o None)."""
    semanas = max(2, min(16, int(semanas or 8)))
    cd_pendientes = cd_pendientes or []
    horas = horas_semanales(perfil)
    candidatos = priorizar_cursos(cursos, perfil.get("pga_acumulado"))
    n = numero_cursos_foco(horas, len(candidatos))
    sel = candidatos[:n]
    reparto = repartir_horas(horas, [c["puntaje"] for c in sel])
    foco = []
    for c, h in zip(sel, reparto):
        foco.append({
            "curso_id": c["curso_id"], "curso": c["curso"], "area": c.get("area"), "tipo": c["tipo"],
            "prioridad": c["puntaje"], "prob_reprobar": c["prob_reprobar"],
            "motivos": c["motivos"] or ["curso relevante de tu semestre"],
            "horas_semana": h, "objetivo": _objetivo(c),
            "recursos": recursos_para(c["curso_id"], c.get("area") or "", catalogo),
        })
    rec = catalogo.get("recursos", {})
    riesgo = perfil.get("riesgo") or {}
    return {
        "estudiante": perfil.get("nombre"),
        "semanas": semanas,
        "horas_semana": horas,
        "criterio_horas": "Horas de estudio autónomo adicionales a las clases, según riesgo del modelo "
                          f"({riesgo.get('nivel', 'sin dato')}), estado académico "
                          f"({perfil.get('estado_academico') or 'sin dato'}), carga actual "
                          f"({perfil.get('creditos_en_curso') or 0} créditos) y si trabaja "
                          f"({'sí' if perfil.get('trabaja') else 'no'}).",
        "cursos_foco": foco,
        "plan_semanal": plan_semanal(foco, semanas) if foco else [],
        "estrategias": ESTRATEGIAS,
        "consejos_perfil": consejos_perfil(perfil.get("riesgo")),
        "hitos": [{"semana": k, "hito": v} for k, v in sorted(hitos_autoevaluacion(semanas).items())],
        "aprender_a_aprender": [{"id": i, **rec[i]} for i in catalogo.get("transversales", []) if i in rec][:3],
        "apoyo_unab": servicios_apoyo(perfil, foco, cd_pendientes),
        "fundamento": "Educación de precisión: los cursos foco y las horas salen de tus datos (estado de cada curso, "
                      "tasa histórica de reprobación ajustada por tu PGA, cadena de prerrequisitos y factores del "
                      "modelo de riesgo). Autoaprendizaje: estrategias con evidencia (Dunlosky et al., 2013) dentro "
                      "del ciclo de autorregulación de Zimmerman (2002).",
        "recursos_verificados": catalogo.get("verificado"),
    }


def resumen_ruta(ruta: dict, max_recursos: int = 3) -> dict:
    """Versión compacta para /api/dashboard (app móvil)."""
    return {
        "semanas": ruta["semanas"],
        "horas_semana": ruta["horas_semana"],
        "cursos_foco": [{
            "curso_id": c["curso_id"], "curso": c["curso"], "tipo": c["tipo"], "motivo": "; ".join(c["motivos"][:2]),
            "horas_semana": c["horas_semana"], "objetivo": c["objetivo"],
            "recursos": [{k: r[k] for k in ("titulo", "proveedor", "url", "tipo", "idioma", "horas")}
                         for r in c["recursos"][:max_recursos]],
        } for c in ruta["cursos_foco"]],
        "estrategias": [{"nombre": e["nombre"], "como": e["como"]} for e in ruta["estrategias"]],
        "consejos": ruta["consejos_perfil"],
        "hitos": ruta["hitos"],
        "apoyo_unab": ruta["apoyo_unab"],
    }
