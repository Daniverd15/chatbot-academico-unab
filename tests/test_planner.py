import sys
from pathlib import Path

# Import with sys.path insert of mcp_server as requested
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))

import random

from planner import Curso, siguiente_periodo, camino_critico, planificar, prob_aprobar, montecarlo


def make_curso(
    curso_id,
    nombre=None,
    creditos=3,
    semestre=1,
    prereqs=(),
    cred_min=0,
    tasa_rep=0.1,
):
    return Curso(
        curso_id=curso_id,
        nombre=nombre or curso_id,
        creditos=creditos,
        semestre=semestre,
        prereqs=tuple(prereqs),
        cred_min=cred_min,
        tasa_rep=tasa_rep,
    )


def test_siguiente_periodo_arithmetic_across_years():
    assert siguiente_periodo("2024-1", 1) == "2024-2"
    assert siguiente_periodo("2024-2", 1) == "2025-1"
    assert siguiente_periodo("2023-2", 2) == "2024-2"
    assert siguiente_periodo("2025-1", 3) == "2026-2"
    assert siguiente_periodo("2020-1", 0) == "2020-1"


def test_camino_critico_basic():
    # A -> B -> C chain
    cursos = {
        "A": make_curso("A"),
        "B": make_curso("B", prereqs=("A",)),
        "C": make_curso("C", prereqs=("B",)),
    }
    cc = camino_critico(cursos)
    assert cc["A"] == 3
    assert cc["B"] == 2
    assert cc["C"] == 1


def test_prerequisites_respected_in_every_planned_semester():
    cursos = {
        "A": make_curso("A", creditos=3),
        "B": make_curso("B", creditos=3, prereqs=("A",)),
        "C": make_curso("C", creditos=3, prereqs=("B",)),
        "D": make_curso("D", creditos=3, prereqs=("A",)),
    }
    plan = planificar(cursos, aprobados=set(), creditos_aprobados=0, max_creditos=18)
    aprobados = set()
    for sem in plan:
        for cid in sem:
            curso = cursos[cid]
            assert all(p in aprobados for p in curso.prereqs), (
                f"Prereq violated for {cid} in semester {sem}, aprobados={aprobados}"
            )
        aprobados.update(sem)
    assert set(cursos).issubset(aprobados)


def test_credit_cap_respected():
    cursos = {
        f"C{i}": make_curso(f"C{i}", creditos=4, semestre=i)
        for i in range(1, 7)
    }
    max_creditos = 9
    plan = planificar(cursos, aprobados=set(), creditos_aprobados=0, max_creditos=max_creditos)
    for sem in plan:
        carga = sum(cursos[cid].creditos for cid in sem)
        assert carga <= max_creditos, f"Semester {sem} exceeds cap: {carga} > {max_creditos}"


def test_minimum_credits_requirement_cred_min():
    cursos = {
        "BAS1": make_curso("BAS1", creditos=6),
        "BAS2": make_curso("BAS2", creditos=6),
        "ADV": make_curso("ADV", creditos=3, prereqs=(), cred_min=10),
    }
    plan = planificar(cursos, aprobados=set(), creditos_aprobados=0, max_creditos=18)
    aprobados = set()
    creds = 0
    for sem in plan:
        for cid in sem:
            assert creds >= cursos[cid].cred_min, (
                f"{cid} scheduled with creds={creds} < cred_min={cursos[cid].cred_min}"
            )
        for cid in sem:
            aprobados.add(cid)
            creds += cursos[cid].creditos
    assert "ADV" in aprobados
    # ADV must not appear in the first semester since starting credits 0 < 10
    assert "ADV" not in plan[0]


def test_isis5901_practice_scheduled_alone_and_last():
    # ISIS5901 should be scheduled alone and only when it is the last pending course.
    cursos = {
        "C1": make_curso("C1", creditos=3),
        "C2": make_curso("C2", creditos=3),
        "ISIS5901": make_curso("ISIS5901", nombre="Práctica", creditos=6, prereqs=("C1", "C2")),
    }
    plan = planificar(cursos, aprobados=set(), creditos_aprobados=0, max_creditos=18)
    # All courses planned
    all_planned = [cid for sem in plan for cid in sem]
    assert set(all_planned) == set(cursos.keys())
    # ISIS5901 must be alone in its semester and in the last semester
    practica_sem_idx = next(i for i, sem in enumerate(plan) if "ISIS5901" in sem)
    assert plan[practica_sem_idx] == ["ISIS5901"]
    assert practica_sem_idx == len(plan) - 1


def test_empty_plan_when_everything_approved():
    cursos = {
        "A": make_curso("A"),
        "B": make_curso("B", prereqs=("A",)),
    }
    plan = planificar(
        cursos,
        aprobados={"A", "B"},
        creditos_aprobados=6,
        max_creditos=18,
    )
    assert plan == []


def test_prob_aprobar_bounded():
    for pga in [0.0, 1.0, 2.0, 3.0, 3.55, 4.0, 5.0, 10.0, None]:
        for tasa_rep in [0.0, 0.01, 0.1, 0.5, 0.9, 0.99, 1.0]:
            p = prob_aprobar(pga, tasa_rep)
            assert 0.35 <= p <= 0.99, f"Out of bounds for pga={pga}, tasa_rep={tasa_rep}: {p}"


def test_prob_aprobar_monotonic_in_pga():
    tasa_rep = 0.2
    pgas = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    probs = [prob_aprobar(pga, tasa_rep) for pga in pgas]
    for i in range(len(probs) - 1):
        assert probs[i] <= probs[i + 1], (
            f"Not monotonic: PGA {pgas[i]}->{pgas[i+1]} gave {probs[i]}->{probs[i+1]}"
        )
    # strictly increasing in a reasonable range (not clamped at both ends)
    assert probs[0] < probs[-1]


def test_montecarlo_p90_ge_p50_and_deterministic():
    cursos = {
        "A": make_curso("A", creditos=3, tasa_rep=0.1),
        "B": make_curso("B", creditos=3, prereqs=("A",), tasa_rep=0.2),
        "C": make_curso("C", creditos=3, prereqs=("B",), tasa_rep=0.3),
        "D": make_curso("D", creditos=3, tasa_rep=0.15),
        "E": make_curso("E", creditos=3, prereqs=("D",), tasa_rep=0.25),
    }
    aprobados = set()
    creditos_aprobados = 0
    pga = 3.5
    max_creditos = 9

    r1 = montecarlo(cursos, aprobados, creditos_aprobados, pga, max_creditos, simulaciones=200, seed=42)
    r2 = montecarlo(cursos, aprobados, creditos_aprobados, pga, max_creditos, simulaciones=200, seed=42)
    r3 = montecarlo(cursos, aprobados, creditos_aprobados, pga, max_creditos, simulaciones=200, seed=99)

    assert r1["semestres_p90"] >= r1["semestres_p50"]
    assert r1 == r2, "Montecarlo not deterministic with same seed"
    # different seed may differ (sanity check that seed is used) - not strictly required but likely
    assert "semestres_p50" in r1 and "semestres_p90" in r1
    assert "semestres_promedio" in r1
    assert isinstance(r1["cursos_con_mayor_riesgo_de_reprobar"], list)


def test_practica_no_se_programa_con_cursos_bloqueados():
    import planner as pl
    cursos = {
        "A": pl.Curso("A", "A", 3, 1, (), 0, 0.1),
        "B": pl.Curso("B", "B", 3, 2, (), 999, 0.1),
        "ISIS5901": pl.Curso("ISIS5901", "Practica", 12, 9, (), 0, 0.1),
    }
    plan = pl.planificar(cursos, set(), 0)
    assert all("ISIS5901" not in sem for sem in plan)
    assert not pl.plan_completo(cursos, set(), plan)


def test_montecarlo_cuenta_incompletas():
    import planner as pl
    cursos = {"B": pl.Curso("B", "B", 3, 2, (), 999, 0.1)}
    r = pl.montecarlo(cursos, set(), 0, 3.5, 18, simulaciones=20)
    assert r["simulaciones_incompletas"] == 20 and r["semestres_p50"] == 24
