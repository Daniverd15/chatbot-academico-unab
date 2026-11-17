"""
Generador de datos sintéticos que simula Banner/COSMOS para Ingeniería de Sistemas.

Simulación por agentes: cada estudiante tiene una "habilidad" latente
(correlacionada con su puntaje Saber 11) y avanza periodo a periodo:

  1. Inscribe cursos habilitados (prerrequisitos + créditos mínimos), priorizando
     repetir los reprobados y respetando su carga máxima (menor si trabaja).
  2. Obtiene una nota ~ N(μ, σ) donde μ depende de la habilidad, la dificultad
     del curso y la fatiga por sobrecarga.
  3. Se calcula el PGA del periodo y el estado académico (Reglamento UNAB 2019
     art. 24); dos periodos en prueba académica ⇒ fuera del programa.
  4. Puede desertar con probabilidad que crece con el bajo rendimiento.

También simula la ruta de Competencias Digitales (CCD), la prueba diagnóstica
(umbral 70 %), la oferta antigua homologable y los requisitos de grado.

Salida: CSVs en data/synthetic/ listos para COPY a PostgreSQL.
Uso:    python database/generate_synthetic_data.py --estudiantes 420 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

from catalogo import CD_CURSOS, CURSOS, DESCRIPCIONES, PROGRAMA, REQUISITOS_GRADO

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"

PERIODO_ACTUAL = "2026-2"
PERIODOS = [f"{a}-{n}" for a in range(2021, 2027) for n in (1, 2)]
VALOR_SEMESTRE = 9_850_000  # matrícula plena simulada (COP)

CURSO = {c[0]: c for c in CURSOS}
PRE: dict[str, list[str]] = {c[0]: [p for p in c[8] if not p.startswith("CRED:")] for c in CURSOS}
CRED_MIN: dict[str, int] = {
    c[0]: max([int(p.split(":")[1]) for p in c[8] if p.startswith("CRED:")] or [0]) for c in CURSOS
}

# Cuentas demo con escenarios didácticos (PIN 1234)
DEMO = {
    "U00100001": dict(nombres="Valentina", apellidos="Rojas Duarte", cohorte="2024-1", habilidad=1.6, trabaja=False),
    "U00100002": dict(nombres="Andrés Felipe", apellidos="Gómez Pinzón", cohorte="2025-1", habilidad=-1.25, trabaja=True),
    "U00100003": dict(nombres="Laura Camila", apellidos="Martínez Ardila", cohorte="2022-1", habilidad=0.55, trabaja=False),
    "U00100004": dict(nombres="Santiago", apellidos="Herrera Quintero", cohorte="2026-2", habilidad=0.3, trabaja=False),
    "U00100005": dict(nombres="María José", apellidos="Castillo Vera", cohorte="2023-2", habilidad=0.05, trabaja=True),
}


def fechas_periodo(pid: str) -> tuple[date, date]:
    anio, num = map(int, pid.split("-"))
    return (date(anio, 2, 2), date(anio, 6, 12)) if num == 1 else (date(anio, 8, 3), date(anio, 11, 27))


def hash_pin(codigo: str, pin: str) -> str:
    return hashlib.sha256(f"{codigo}:{pin}".encode()).hexdigest()


def estado_academico(pga: float, prev_estado: str | None) -> str:
    """Reglamento Estudiantil de Pregrado UNAB 2019, artículo 24."""
    if pga > 3.20:
        return "Normal"
    if pga >= 3.00:
        return "En prueba académica" if prev_estado in ("Condicional", "En prueba académica") else "Condicional"
    return "En prueba académica"


@dataclass
class Est:
    codigo: str
    cohorte: str
    habilidad: float
    trabaja: bool
    aprobados: set[str] = field(default_factory=set)
    creditos: int = 0
    reprobados: dict[str, int] = field(default_factory=dict)
    estados: list[str] = field(default_factory=list)
    activo: bool = True
    condicion: str = "Activo"


def habilitados(e: Est) -> list[str]:
    out = []
    for cid in CURSO:
        if cid in e.aprobados:
            continue
        if all(p in e.aprobados for p in PRE[cid]) and e.creditos >= CRED_MIN[cid]:
            out.append(cid)
    # reprobados primero, luego por semestre sugerido
    out.sort(key=lambda c: (0 if c in e.reprobados else 1, CURSO[c][3]))
    return out


def nota(rng: np.random.Generator, e: Est, cid: str, carga: int, intento: int) -> float:
    dif = CURSO[cid][7]
    mu = 3.55 + 0.42 * e.habilidad - 1.35 * (dif - 0.45) - 0.05 * max(0, carga - 18)
    mu += 0.18 * (intento - 1)  # aprende del intento anterior
    mu -= 0.15 if e.trabaja else 0
    n = rng.normal(mu, 0.55)
    return float(np.clip(round(n, 1), 0.0, 5.0))


def main(n_est: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    random.seed(seed)
    fake = Faker("es_CO")
    Faker.seed(seed)
    OUT.mkdir(parents=True, exist_ok=True)

    rows = {k: [] for k in [
        "programa", "periodo", "curso", "prerrequisito", "requisito_grado", "cd_curso", "estudiante",
        "matricula", "inscripcion", "estudiante_requisito", "cd_inscripcion", "cd_prueba_diagnostica",
    ]}

    # ----------------------------- catálogos -----------------------------
    rows["programa"].append(PROGRAMA)
    for pid in PERIODOS:
        ini, fin = fechas_periodo(pid)
        a, n = map(int, pid.split("-"))
        rows["periodo"].append(dict(periodo_id=pid, anio=a, numero=n, fecha_inicio=ini, fecha_fin=fin,
                                    es_actual=pid == PERIODO_ACTUAL))
    for c in CURSOS:
        rows["curso"].append(dict(curso_id=c[0], programa_id="ISIS", nombre=c[1], creditos=c[2],
                                  semestre_sugerido=c[3], componente=c[4], area=c[5], tipo=c[6],
                                  dificultad=c[7], descripcion=DESCRIPCIONES.get(c[0], "")))
        for p in c[8]:
            if p.startswith("CRED:"):
                rows["prerrequisito"].append(dict(curso_id=c[0], requisito_id=None,
                                                  creditos_min=int(p[5:]), tipo="creditos"))
            else:
                rows["prerrequisito"].append(dict(curso_id=c[0], requisito_id=p, creditos_min=None,
                                                  tipo="prerrequisito"))
    for r in REQUISITOS_GRADO:
        rows["requisito_grado"].append(dict(requisito_id=r[0], nombre=r[1], descripcion=r[2]))
    for c in CD_CURSOS:
        rows["cd_curso"].append(dict(cd_curso_id=c[0], nombre=c[1], ruta=c[2], ruta_nombre=c[3], horas=c[4],
                                     modalidad=c[5], vigente=c[6], equivale_a=c[7], descripcion=c[8]))

    # ----------------------------- estudiantes -----------------------------
    # cohortes más recientes son más grandes (efecto deserción)
    pesos = np.array([0.6 + 0.08 * i for i in range(len(PERIODOS))])
    pesos /= pesos.sum()
    codigos_usados = set(DEMO)
    estudiantes: list[tuple[Est, dict]] = []

    for i in range(n_est):
        if i < len(DEMO):
            codigo = list(DEMO)[i]
            d = DEMO[codigo]
            cohorte, hab, trabaja = d["cohorte"], d["habilidad"], d["trabaja"]
            nombres, apellidos = d["nombres"], d["apellidos"]
            genero = "F" if codigo in ("U00100001", "U00100003", "U00100005") else "M"
            saber = int(np.clip(300 + 45 * hab + rng.normal(0, 15), 220, 470))
        else:
            while True:
                codigo = f"U00{rng.integers(150000, 199999)}"
                if codigo not in codigos_usados:
                    codigos_usados.add(codigo)
                    break
            cohorte = str(rng.choice(PERIODOS, p=pesos))
            genero = str(rng.choice(["M", "F", "O"], p=[0.68, 0.31, 0.01]))
            nombres = fake.first_name_male() if genero == "M" else fake.first_name_female()
            apellidos = f"{fake.last_name()} {fake.last_name()}"
            saber = int(np.clip(rng.normal(305, 38), 200, 480))
            hab = float((saber - 305) / 38 * 0.6 + rng.normal(0, 0.8))
            trabaja = bool(rng.random() < 0.22)

        anio_coh = int(cohorte[:4])
        e = Est(codigo, cohorte, hab, trabaja)
        meta = dict(
            codigo=codigo,
            documento=str(rng.integers(1_000_000_000, 1_099_999_999)),
            nombres=nombres, apellidos=apellidos,
            email=f"{nombres.split()[0].lower()}.{apellidos.split()[0].lower()}{codigo[-3:]}@unab.edu.co"
            .translate(str.maketrans("áéíóúñü", "aeiounu")),
            genero=genero,
            fecha_nacimiento=date(anio_coh - int(rng.integers(16, 21)), int(rng.integers(1, 13)), int(rng.integers(1, 28))),
            ciudad_origen=str(rng.choice(["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta", "Cúcuta",
                                          "Barrancabermeja", "San Gil", "Valledupar", "Bogotá", "Socorro"],
                                         p=[.34, .16, .07, .08, .1, .07, .05, .04, .05, .04])),
            colegio_tipo=str(rng.choice(["Público", "Privado"], p=[0.42, 0.58])),
            puntaje_saber11=saber, programa_id="ISIS", cohorte=cohorte, condicion="Activo",
            trabaja=trabaja,
            beca=(str(rng.choice(["Beca de excelencia", "Generación E", "Convenio empresarial", "Deportiva"]))
                  if rng.random() < 0.18 else None),
            pin_acceso=hash_pin(codigo, "1234"),
        )
        estudiantes.append((e, meta))

    # ----------------------------- simulación -----------------------------
    for e, meta in estudiantes:
        es_demo = e.codigo in DEMO
        idx0 = PERIODOS.index(e.cohorte)
        for pid in PERIODOS[idx0:]:
            ini, fin = fechas_periodo(pid)
            actual = pid == PERIODO_ACTUAL
            if not e.activo:
                break
            # reserva de cupo esporádica
            if not es_demo and not actual and rng.random() < 0.025:
                rows["matricula"].append(dict(codigo=e.codigo, periodo_id=pid, estado="Reserva de cupo",
                                              fecha_matricula=ini - timedelta(days=20), valor_liquidado=0,
                                              valor_pagado=0, creditos_inscritos=0))
                continue

            carga_max = int(rng.integers(12, 16)) if e.trabaja else int(rng.integers(16, 21))
            if e.estados and e.estados[-1] == "En prueba académica":
                carga_max = min(carga_max, 14)  # restricción de carga en prueba académica
            cursos, carga = [], 0
            for cid in habilitados(e):
                cr = CURSO[cid][2]
                if carga + cr <= carga_max or (cid == "ISIS5901" and not cursos):
                    cursos.append(cid)
                    carga += cr
            if not cursos:  # terminó el plan
                e.activo = False
                e.condicion = "Graduado" if rng.random() < 0.7 else "Egresado"
                break

            if actual:
                r = rng.random()
                est_mat = ("Matriculado" if r < 0.80 or es_demo else
                           "Pendiente de pago" if r < 0.91 else "Pre-matriculado")
                if e.codigo == "U00100005":
                    est_mat = "Pendiente de pago"
            else:
                est_mat = "Matriculado"
            valor = VALOR_SEMESTRE if carga > 10 else int(VALOR_SEMESTRE * carga / 16)
            pagado = valor if est_mat == "Matriculado" else (int(valor * 0.5) if est_mat == "Pendiente de pago" else 0)
            rows["matricula"].append(dict(codigo=e.codigo, periodo_id=pid, estado=est_mat,
                                          fecha_matricula=ini - timedelta(days=int(rng.integers(5, 30))),
                                          valor_liquidado=valor, valor_pagado=pagado, creditos_inscritos=carga))

            puntos, creds_eval = 0.0, 0
            for cid in cursos:
                intento = e.reprobados.get(cid, 0) + 1
                if actual:
                    rows["inscripcion"].append(dict(codigo=e.codigo, curso_id=cid, periodo_id=pid,
                                                    nota_final=None, estado="Cursando"))
                    continue
                if rng.random() < 0.03:
                    rows["inscripcion"].append(dict(codigo=e.codigo, curso_id=cid, periodo_id=pid,
                                                    nota_final=None, estado="Cancelado"))
                    continue
                n = nota(rng, e, cid, carga, intento)
                ok = n >= 3.0
                rows["inscripcion"].append(dict(codigo=e.codigo, curso_id=cid, periodo_id=pid, nota_final=n,
                                                estado="Aprobado" if ok else "Reprobado"))
                cr = CURSO[cid][2]
                puntos += n * cr
                creds_eval += cr
                if ok:
                    e.aprobados.add(cid)
                    e.creditos += cr
                    e.reprobados.pop(cid, None)
                else:
                    e.reprobados[cid] = e.reprobados.get(cid, 0) + 1

            if actual or creds_eval == 0:
                continue
            pga = puntos / creds_eval
            prev = e.estados[-1] if e.estados else None
            est = estado_academico(pga, prev)
            # dos periodos consecutivos en prueba ⇒ fuera del programa (no aplica a demos)
            if est == "En prueba académica" and prev == "En prueba académica" and not es_demo:
                e.activo, e.condicion = False, "Inactivo"
            e.estados.append(est)
            # deserción
            p_des = 0.025 + (0.07 if pga < 3.0 else 0) + (0.03 if e.trabaja else 0)
            if not es_demo and e.activo and rng.random() < p_des:
                e.activo, e.condicion = False, str(rng.choice(["Desertor", "Retirado"], p=[0.7, 0.3]))

        meta["condicion"] = e.condicion
        if e.activo and not any(r["codigo"] == e.codigo and r["periodo_id"] == PERIODO_ACTUAL
                                for r in rows["matricula"][-3:]):
            # activo pero sin matrícula en el periodo actual
            meta["condicion"] = "Activo"
            rows["matricula"].append(dict(codigo=e.codigo, periodo_id=PERIODO_ACTUAL, estado="No matriculado",
                                          fecha_matricula=None, valor_liquidado=VALOR_SEMESTRE, valor_pagado=0,
                                          creditos_inscritos=0))

        # ------------------ competencias digitales ------------------
        sim_cd(rng, e, rows)
        # ------------------ requisitos de grado ------------------
        ingles_ok = "ISIS2406" in e.aprobados and (rng.random() < 0.75 or e.codigo == "U00100001")
        if e.codigo == "U00100003":
            ingles_ok = False
        rows["estudiante_requisito"].append(dict(
            codigo=e.codigo, requisito_id="INGLES_B1", cumplido=ingles_ok,
            fecha=date(2026, 5, 20) if ingles_ok else None,
            detalle="Prueba institucional B1 aprobada" if ingles_ok else "Pendiente de acreditar B1"))
        saber_ok = e.creditos >= 125 and rng.random() < 0.8
        rows["estudiante_requisito"].append(dict(
            codigo=e.codigo, requisito_id="SABER_PRO", cumplido=saber_ok,
            fecha=date(2026, 8, 30) if saber_ok else None,
            detalle="Presentado" if saber_ok else "No presentado"))
        paz = rng.random() < 0.9
        rows["estudiante_requisito"].append(dict(
            codigo=e.codigo, requisito_id="PAZ_SALVO", cumplido=paz, fecha=None,
            detalle=None if paz else "Deuda en biblioteca"))
        rows["estudiante"].append(meta)

    # CD_RUTAS se deriva de cd_inscripcion en la vista, pero dejamos el registro
    for e, _ in estudiantes:
        rows["estudiante_requisito"].append(dict(codigo=e.codigo, requisito_id="CD_RUTAS", cumplido=False,
                                                 fecha=None, detalle="Calculado en v_competencias_digitales"))

    for name, data in rows.items():
        write_csv(OUT / f"{name}.csv", data)
    resumen(rows)


def sim_cd(rng: np.random.Generator, e: Est, rows: dict) -> None:
    """Simula la ruta de Competencias Digitales según la cohorte."""
    idx0 = PERIODOS.index(e.cohorte)
    periodos_est = PERIODOS[idx0:]
    r2_opts = ["CD-R2-AD", "CD-R2-MP", "CD-R2-CC"]
    r3_opts = ["CD-R3-IA", "CD-R3-ML", "CD-R3-CB"]

    def add(cid, pid, estado, nota=None, ciclo=None):
        ini, fin = fechas_periodo(pid)
        rows["cd_inscripcion"].append(dict(codigo=e.codigo, cd_curso_id=cid, periodo_id=pid,
                                           ciclo=ciclo or str(rng.choice(["Mensual 1", "Mensual 2", "Mensual 3",
                                                                          "Mensual 4", "Vacacional"])),
                                           estado=estado, nota=nota, fecha=fin))

    def cursar(cid, pid):
        if pid == PERIODO_ACTUAL:
            add(cid, pid, "Cursando")
            return True
        n = float(np.clip(round(rng.normal(4.0 + 0.2 * e.habilidad, 0.5), 1), 1.5, 5.0))
        add(cid, pid, "Aprobado" if n >= 3.0 else "Reprobado", n)
        return n >= 3.0

    hecho = {1: False, 2: False, 3: False}
    # Oferta antigua (cohortes anteriores a 2025-2): cursos ofimáticos hasta 2025
    if e.cohorte < "2025-2":
        old_p = [p for p in periodos_est if p <= "2025-2"]
        for cid, ruta, prob in [("CD-OLD-CDV", 1, 0.75), ("CD-OLD-EXC", 2, 0.6), ("CD-OLD-PPT", 2, 0.35),
                                ("CD-OLD-WRD", None, 0.5)]:
            if old_p and rng.random() < prob:
                ok = cursar(cid, str(rng.choice(old_p[:4])))
                if ok and ruta and not hecho[ruta]:
                    hecho[ruta] = True
    else:
        # Prueba diagnóstica de primer ingreso
        demo_score = {"U00100004": 82.0, "U00100002": 58.5}
        score = demo_score.get(e.codigo, float(np.clip(rng.normal(66 + 6 * e.habilidad, 13), 15, 100)))
        ini, _ = fechas_periodo(e.cohorte)
        rows["cd_prueba_diagnostica"].append(dict(codigo=e.codigo, fecha=ini + timedelta(days=4),
                                                  puntaje=round(score, 2)))
        if score >= 70:
            add("CD-R1-ID", e.cohorte, "Validado por prueba", None, "Prueba diagnóstica")
            hecho[1] = True

    # Nueva oferta (2026-1 en adelante)
    new_p = [p for p in periodos_est if p >= "2026-1"]
    disciplina = 0.55 + 0.12 * e.habilidad
    if e.codigo == "U00100003":
        disciplina = 0.0  # escenario: cerca de grado sin la ruta CD completa
    if e.codigo == "U00100001":
        disciplina = 1.0
    for ruta, opts in [(1, ["CD-R1-ID"]), (2, r2_opts), (3, r3_opts)]:
        if hecho[ruta] or not new_p:
            continue
        if rng.random() < disciplina:
            pick = "CD-R3-IA" if (ruta == 3 and rng.random() < 0.55) else str(rng.choice(opts))
            if e.codigo == "U00100001":
                pick = {1: "CD-R1-ID", 2: "CD-R2-AD", 3: "CD-R3-IA"}[ruta]
            hecho[ruta] = cursar(pick, str(rng.choice(new_p)))


def write_csv(path: Path, data: list[dict]) -> None:
    if not data:
        path.write_text("")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader()
        for r in data:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def resumen(rows: dict) -> None:
    print("Datos sintéticos generados en", OUT)
    for k, v in rows.items():
        print(f"  {k:<24} {len(v):>7} filas")
    notas = [r["nota_final"] for r in rows["inscripcion"] if r["nota_final"] not in (None, "")]
    rep = sum(1 for r in rows["inscripcion"] if r["estado"] == "Reprobado")
    print(f"  nota media={np.mean(notas):.2f}  tasa reprobación={rep / max(1, len(notas)):.1%}")
    print(f"  créditos del plan={PROGRAMA['creditos_totales']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--estudiantes", type=int, default=420)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    main(a.estudiantes, a.seed)
