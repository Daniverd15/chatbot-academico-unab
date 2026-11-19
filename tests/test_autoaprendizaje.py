"""Pruebas de la ruta de autoaprendizaje (lógica pura: sin red ni base de datos)."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))

import pytest

import autoaprendizaje as aa

CATALOGO_REAL = Path(__file__).resolve().parents[1] / "mcp_server" / "recursos_aprendizaje.json"


def curso(cid, estado="Pendiente", habilitado=False, tasa=15, bloquea=0, nota=None, rep=0, prereqs=(),
          area="Programación", sem=1):
    return {"curso_id": cid, "curso": f"Curso {cid}", "area": area, "estado": estado, "habilitado": habilitado,
            "tasa_reprobacion": tasa, "cursos_que_bloquea": bloquea, "nota_aprobacion": nota,
            "veces_reprobado": rep, "prereqs": list(prereqs), "semestre_sugerido": sem, "creditos": 3}


CATALOGO = {
    "verificado": "2026-11-19",
    "recursos": {
        "r1": {"titulo": "Recurso 1", "proveedor": "P", "url": "https://a.org/1", "tipo": "curso", "idioma": "es", "horas": 10},
        "r2": {"titulo": "Recurso 2", "proveedor": "P", "url": "https://a.org/2", "tipo": "video", "idioma": "en", "horas": 3},
        "r3": {"titulo": "Recurso 3", "proveedor": "P", "url": "https://a.org/3", "tipo": "práctica", "idioma": "es", "horas": 5},
        "t1": {"titulo": "Aprender", "proveedor": "P", "url": "https://a.org/t", "tipo": "curso", "idioma": "es", "horas": 15},
    },
    "cursos": {"C1": ["r1", "r2"], "C2": ["r3"]},
    "areas": {"Matemáticas": ["r2"]},
    "transversales": ["t1"],
}

PERFIL = {"nombre": "Ana", "estado_academico": "Normal", "pga_acumulado": 3.6, "trabaja": False,
          "creditos_en_curso": 16, "riesgo": {"nivel": "medio", "factores": []}}


# --- priorización --------------------------------------------------------
def test_cursando_y_repitencia_van_primero():
    cursos = [
        curso("C1", "Cursando", tasa=10),
        curso("C2", "Cursando", tasa=30, rep=1),
        curso("C3", "Pendiente", habilitado=True, tasa=40),
        curso("C4", "Pendiente", habilitado=False, tasa=60),      # no habilitado → fuera
        curso("C5", "Aprobado", nota=4.5),                          # aprobado con buena nota → fuera
    ]
    out = aa.priorizar_cursos(cursos, 3.5)
    ids = [c["curso_id"] for c in out]
    assert ids[0] == "C2" and out[0]["tipo"] == "repitencia"
    assert "C4" not in ids and "C5" not in ids
    assert ids.index("C1") < ids.index("C3")


def test_mayor_tasa_de_reprobacion_sube_prioridad():
    out = aa.priorizar_cursos([curso("A", "Cursando", tasa=5), curso("B", "Cursando", tasa=45)], 3.4)
    assert out[0]["curso_id"] == "B"
    assert out[0]["prob_reprobar"] > out[1]["prob_reprobar"]
    assert any("riesgo de reprobar" in m for m in out[0]["motivos"])


def test_pga_alto_reduce_riesgo_estimado():
    c = [curso("A", "Cursando", tasa=35)]
    assert aa.priorizar_cursos(c, 4.5)[0]["prob_reprobar"] < aa.priorizar_cursos(c, 3.0)[0]["prob_reprobar"]


def test_refuerzo_de_base_solo_si_habilita_pendientes():
    cursos = [
        curso("BASE", "Aprobado", nota=3.1, area="Matemáticas"),
        curso("BASE_OK", "Aprobado", nota=3.2),                     # nota baja pero no habilita nada pendiente
        curso("SIG", "Pendiente", habilitado=True, prereqs=["BASE"]),
        curso("OTRO", "Aprobado", nota=4.0, prereqs=["BASE_OK"]),
    ]
    out = {c["curso_id"]: c for c in aa.priorizar_cursos(cursos, 3.4)}
    assert out["BASE"]["tipo"] == "refuerzo"
    assert "3.1" in out["BASE"]["motivos"][0]
    assert "BASE_OK" not in out


def test_cuello_de_botella_suma_puntaje():
    a, b = aa.priorizar_cursos([curso("A", "Cursando", bloquea=6), curso("B", "Cursando", bloquea=0)], 3.5)
    assert a["curso_id"] == "A" and a["puntaje"] > b["puntaje"]


# --- horas y reparto ------------------------------------------------------
@pytest.mark.parametrize("perfil,esperado", [
    ({"riesgo": {"nivel": "bajo"}}, 5),
    ({"riesgo": {"nivel": "alto"}, "estado_academico": "En prueba académica"}, 11),
    ({"riesgo": {"nivel": "alto"}, "trabaja": True}, 7),
    ({"riesgo": {"nivel": "bajo"}, "trabaja": True, "creditos_en_curso": 20}, 4),  # tope inferior
    ({"riesgo": None}, 6),
])
def test_horas_semanales(perfil, esperado):
    assert aa.horas_semanales(perfil) == esperado


def test_trabajar_reduce_horas_y_cursos_foco():
    h_no = aa.horas_semanales({**PERFIL, "trabaja": False})
    h_si = aa.horas_semanales({**PERFIL, "trabaja": True})
    assert h_si < h_no
    assert aa.numero_cursos_foco(h_si, 10) <= aa.numero_cursos_foco(h_no, 10)


@pytest.mark.parametrize("horas,puntajes", [(7, [5.0, 3.0, 1.0]), (4, [1.0, 1.0, 1.0, 1.0]), (12, [9.0, 0.5]),
                                            (5, [6.2, 1.1])])
def test_repartir_horas_suma_exacta_y_minimo(horas, puntajes):
    r = aa.repartir_horas(horas, puntajes)
    assert sum(r) == horas
    assert all(x >= 1 and (x * 2).is_integer() for x in r)
    assert r[0] == max(r)


def test_numero_cursos_foco_entre_2_y_4():
    assert [aa.numero_cursos_foco(h, 10) for h in (4, 5, 6, 8, 9, 12)] == [2, 2, 3, 3, 4, 4]
    assert aa.numero_cursos_foco(9, 1) == 1


# --- plan completo --------------------------------------------------------
def _ruta(semanas=8, perfil=PERFIL, cd=None):
    cursos = [curso("C1", "Cursando", tasa=40, rep=1), curso("C2", "Cursando", tasa=20),
              curso("C3", "Pendiente", habilitado=True, area="Matemáticas"), curso("C9", "Aprobado", nota=4.8)]
    return aa.armar_ruta(perfil, cursos, CATALOGO, semanas, cd or [])


def test_armar_ruta_estructura_y_determinismo():
    r = _ruta()
    assert r == _ruta()
    assert r["semanas"] == 8 and len(r["plan_semanal"]) == 8
    assert 2 <= len(r["cursos_foco"]) <= 4
    assert sum(c["horas_semana"] for c in r["cursos_foco"]) == r["horas_semana"]
    assert r["cursos_foco"][0]["curso_id"] == "C1"
    assert [x["id"] for x in r["cursos_foco"][0]["recursos"]] == ["r1", "r2"]
    # respaldo por área cuando el curso no tiene lista propia
    c3 = next((c for c in r["cursos_foco"] if c["curso_id"] == "C3"), None)
    if c3:
        assert [x["id"] for x in c3["recursos"]] == ["r2"]
    assert {e["id"] for e in r["estrategias"]} == {"recuperacion", "espaciada", "intercalado", "autoexplicacion",
                                                  "zimmerman"}
    assert r["aprender_a_aprender"][0]["id"] == "t1"


def test_fases_de_zimmerman_y_hitos():
    plan = _ruta(8)["plan_semanal"]
    assert plan[0]["fase"] == "Planificación" and "objetivos" in plan[0]
    assert plan[-1]["fase"] == "Autorreflexión"
    assert all(p["fase"] == "Ejecución y monitoreo" for p in plan[1:-1])
    con_hito = [p["semana"] for p in plan if "autoevaluacion" in p]
    assert con_hito == [1, 4, 8]
    assert "repaso" not in plan[0] and "semana 3 y 1" in plan[3]["repaso"]
    assert all(s["recurso"] for s in plan[2]["sesiones"] if s["curso_id"] in ("C1", "C2"))


def test_recursos_avanzan_a_lo_largo_de_la_ruta():
    plan = _ruta(8)["plan_semanal"]
    c1 = [next(s for s in p["sesiones"] if s["curso_id"] == "C1")["recurso"]["url"] for p in plan]
    assert c1[0] == "https://a.org/1" and c1[-1] == "https://a.org/2"


def test_semanas_se_acotan():
    assert _ruta(1)["semanas"] == 2
    assert _ruta(40)["semanas"] == 16
    assert len(aa.hitos_autoevaluacion(12)) == 5


def test_apoyo_unab_segun_perfil():
    perfil = {**PERFIL, "estado_academico": "En prueba académica", "trabaja": True,
              "riesgo": {"nivel": "alto", "factores": [
                  {"feature": "reprobados_por_periodo", "efecto": "aumenta"},
                  {"feature": "pga_acumulado", "efecto": "reduce"},
                  {"feature": "trabaja", "efecto": "aumenta"}]}}
    r = _ruta(perfil=perfil, cd=[{"ruta": 3, "ruta_nombre": "Tecnología Transformativa"}])
    servicios = [s["servicio"] for s in r["apoyo_unab"]]
    assert "Programa de Éxito Estudiantil" in servicios
    assert "Bienestar Universitario" in servicios
    assert "Centro de Competencias Digitales" in servicios
    assert len(r["consejos_perfil"]) == 2 and "trabajas" in r["consejos_perfil"][1]


def test_sin_candidatos_no_falla():
    r = aa.armar_ruta(PERFIL, [curso("X", "Aprobado", nota=4.9)], CATALOGO, 8)
    assert r["cursos_foco"] == [] and r["plan_semanal"] == []


def test_resumen_para_dashboard_es_compacto():
    r = _ruta()
    s = aa.resumen_ruta(r, max_recursos=1)
    assert set(s) == {"semanas", "horas_semana", "cursos_foco", "estrategias", "consejos", "hitos", "apoyo_unab"}
    assert all(len(c["recursos"]) <= 1 and c["motivo"] for c in s["cursos_foco"])
    assert "plan_semanal" not in s
    json.dumps(s)  # serializable


# --- catálogo real --------------------------------------------------------
def test_catalogo_real_es_consistente():
    cat = json.loads(CATALOGO_REAL.read_text(encoding="utf-8"))
    rec = cat["recursos"]
    assert len(rec) >= 40
    for r in rec.values():
        assert urlparse(r["url"]).scheme == "https"
        assert r["tipo"] in {"video", "curso", "libro", "práctica"}
        assert r["idioma"] and r["horas"] > 0
    referenciados = {i for ids in [*cat["cursos"].values(), *cat["areas"].values(), cat["transversales"]] for i in ids}
    assert referenciados <= set(rec)
    # todos los cursos regulares del plan simulado tienen recursos (propios o por área)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
    import catalogo
    for cid, _n, _cr, _s, _comp, area, *_ in catalogo.CURSOS:
        assert aa.recursos_para(cid, area, cat), cid
