"""
Proyección de semestres restantes.

1. Plan determinista: programación por listas (list scheduling) sobre el DAG de
   prerrequisitos. En cada semestre se eligen los cursos habilitados con mayor
   "camino crítico" (cuántos semestres encadenados dependen de él), luego por
   semestre sugerido, hasta el tope de créditos.
2. Proyección probabilística (Monte Carlo): repite la simulación N veces
   haciendo que cada curso se apruebe con probabilidad p(estudiante, curso)
   estimada a partir del PGA del estudiante y la tasa histórica de reprobación
   del curso. Devuelve los percentiles P50 / P90 del periodo de grado.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Curso:
    curso_id: str
    nombre: str
    creditos: int
    semestre: int
    prereqs: tuple[str, ...]
    cred_min: int
    tasa_rep: float  # 0..1


def siguiente_periodo(pid: str, n: int = 1) -> str:
    anio, num = map(int, pid.split("-"))
    idx = anio * 2 + (num - 1) + n
    return f"{idx // 2}-{idx % 2 + 1}"


def camino_critico(cursos: dict[str, Curso]) -> dict[str, int]:
    hijos: dict[str, list[str]] = {c: [] for c in cursos}
    for c in cursos.values():
        for p in c.prereqs:
            if p in hijos:
                hijos[p].append(c.curso_id)

    @lru_cache(maxsize=None)
    def prof(cid: str) -> int:
        return 1 + max((prof(h) for h in hijos[cid]), default=0)

    return {c: prof(c) for c in cursos}


def _habilitado(c: Curso, aprobados: set[str], creditos: int) -> bool:
    return all(p in aprobados for p in c.prereqs) and creditos >= c.cred_min


def _simular(cursos, aprobados, creditos_aprobados, max_creditos=18, p_aprobar=None, rng=None, max_semestres=20):
    """Devuelve (plan, aprobados_finales). La práctica (ISIS5901) solo se programa cuando es lo único pendiente."""
    cc = camino_critico(cursos)
    aprob = set(aprobados)
    creds = creditos_aprobados
    plan: list[list[str]] = []
    for _ in range(max_semestres):
        pendientes = [c for c in cursos.values() if c.curso_id not in aprob]
        if not pendientes:
            break
        disp = [c for c in pendientes if _habilitado(c, aprob, creds)]
        disp.sort(key=lambda c: (-cc[c.curso_id], c.semestre, -c.tasa_rep))
        sem, carga = [], 0
        for c in disp:
            if c.curso_id == "ISIS5901":
                if not sem and len(pendientes) == 1:
                    sem.append(c.curso_id)
                    carga = c.creditos
                continue
            if carga + c.creditos <= max_creditos:
                sem.append(c.curso_id)
                carga += c.creditos
        if not sem:  # quedan cursos pero ninguno se puede inscribir: plan incompleto
            break
        plan.append(sem)
        for cid in sem:
            ok = True if p_aprobar is None else (rng or random).random() < p_aprobar.get(cid, 0.85)
            if ok:
                aprob.add(cid)
                creds += cursos[cid].creditos
    return plan, aprob


def planificar(
    cursos: dict[str, Curso],
    aprobados: set[str],
    creditos_aprobados: int,
    max_creditos: int = 18,
    p_aprobar: dict[str, float] | None = None,
    rng: random.Random | None = None,
    max_semestres: int = 20,
) -> list[list[str]]:
    """Devuelve una lista de semestres, cada uno con los curso_id a inscribir."""
    return _simular(cursos, aprobados, creditos_aprobados, max_creditos, p_aprobar, rng, max_semestres)[0]


def plan_completo(cursos: dict[str, Curso], aprobados: set[str], plan: list[list[str]]) -> bool:
    """True si todos los cursos no aprobados aparecen en el plan."""
    planeados = {c for sem in plan for c in sem}
    return all(c in aprobados or c in planeados for c in cursos)


def prob_aprobar(pga: float | None, tasa_rep: float) -> float:
    """p = σ(logit(1 - tasa_rep) + 1.9·(PGA − 3.55)). Acotada a [0.35, 0.99]."""
    base = min(max(1 - tasa_rep, 0.02), 0.98)
    z = math.log(base / (1 - base)) + 1.9 * ((pga or 3.55) - 3.55)
    return min(max(1 / (1 + math.exp(-z)), 0.35), 0.99)


def montecarlo(
    cursos: dict[str, Curso],
    aprobados: set[str],
    creditos_aprobados: int,
    pga: float | None,
    max_creditos: int,
    simulaciones: int = 400,
    seed: int = 7,
) -> dict:
    rng = random.Random(seed)
    p = {cid: prob_aprobar(pga, c.tasa_rep) for cid, c in cursos.items()}
    max_sem = 24
    semestres, incompletas = [], 0
    for _ in range(simulaciones):
        plan, fin = _simular(cursos, aprobados, creditos_aprobados, max_creditos, p, rng, max_sem)
        if all(c in fin for c in cursos):
            semestres.append(len(plan))
        else:  # no terminó: no puede contarse como un plan corto
            semestres.append(max_sem)
            incompletas += 1
    semestres.sort()
    pct = lambda q: semestres[min(len(semestres) - 1, int(q * len(semestres)))]  # noqa: E731
    riesgo = sorted(
        ((cursos[c].nombre, round(1 - p[c], 2)) for c in cursos if c not in aprobados),
        key=lambda x: -x[1],
    )[:5]
    return {
        "semestres_p50": pct(0.5),
        "semestres_p90": pct(0.9),
        "semestres_promedio": round(sum(semestres) / len(semestres), 2),
        "simulaciones_incompletas": incompletas,
        "cursos_con_mayor_riesgo_de_reprobar": [{"curso": n, "prob_reprobar": r} for n, r in riesgo],
    }
