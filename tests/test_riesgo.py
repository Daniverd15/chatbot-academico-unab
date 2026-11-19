"""Explicabilidad del modelo de riesgo académico (sin BD ni red)."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))

import server  # noqa: E402  (no abre conexiones al importar)

MODELO = json.loads(server.RIESGO_PATH.read_text(encoding="utf-8"))


def _estudiante(**kw):
    base = {"pga_acumulado": 2.95, "pga_ultimo_periodo": 2.8, "periodos_cursados": 4,
            "total_reprobados": 6, "creditos_aprobados": 44, "trabaja": True}
    base.update(kw)
    return base


CASOS = [
    _estudiante(),
    _estudiante(pga_acumulado=4.4, pga_ultimo_periodo=4.6, total_reprobados=0, creditos_aprobados=68, trabaja=False),
    _estudiante(pga_ultimo_periodo=None, periodos_cursados=0, total_reprobados=None, creditos_aprobados=None),
]


@pytest.mark.parametrize("r", CASOS)
def test_contribuciones_reproducen_logit(r):
    res = server._riesgo_academico(r)
    z = MODELO["intercepto"] + sum(f["contribucion"] for f in res["factores"])
    p = 1 / (1 + math.exp(-z))
    # contribuciones redondeadas a 3 decimales: tolerancia acorde
    assert p == pytest.approx(res["probabilidad"], abs=1e-3)
    # logit calculado de forma independiente a partir de las variables crudas
    periodos = max(1, r["periodos_cursados"] or 1)
    x = {"pga_acumulado": r["pga_acumulado"], "pga_ultimo_periodo": r["pga_ultimo_periodo"] or r["pga_acumulado"],
         "reprobados_por_periodo": (r["total_reprobados"] or 0) / periodos,
         "creditos_por_periodo": (r["creditos_aprobados"] or 0) / periodos, "trabaja": float(bool(r["trabaja"]))}
    logit = MODELO["intercepto"] + sum(c * (x[k] - MODELO["medias"][k]) / MODELO["desviaciones"][k]
                                       for k, c in MODELO["coeficientes"].items())
    assert z == pytest.approx(logit, abs=5e-3)


@pytest.mark.parametrize("r", CASOS)
def test_factores_ordenados_y_completos(r):
    res = server._riesgo_academico(r)
    fs = res["factores"]
    assert {f["feature"] for f in fs} == set(MODELO["coeficientes"])
    mags = [abs(f["contribucion"]) for f in fs]
    assert mags == sorted(mags, reverse=True)
    for f in fs:
        assert f["etiqueta"] and f["etiqueta"] != f["feature"]
        assert f["efecto"] == ("aumenta" if f["contribucion"] > 0 else "reduce")
        assert f["media"] == pytest.approx(MODELO["medias"][f["feature"]], abs=0.01)


def test_campos_existentes_y_explicacion():
    res = server._riesgo_academico(_estudiante())
    assert {"probabilidad", "nivel", "modelo"} <= set(res)
    assert res["nivel"] in {"alto", "medio", "bajo"}
    assert res["factores"][0]["feature"] == "pga_acumulado"
    assert res["explicacion"].startswith("Lo que más eleva tu riesgo: PGA acumulado bajo (2.95 vs 3.50 del programa)")


def test_sin_pga_no_puntua():
    assert server._riesgo_academico(_estudiante(pga_acumulado=None)) is None
