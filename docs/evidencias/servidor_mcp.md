# Evidencia: servidor MCP (FastMCP)

Generado el 2026-11-19 18:28 con `python scripts/evidencias/generar_evidencias.py mcp`: cliente MCP oficial (Streamable HTTP) contra `https://mcp.35-168-41-252.sslip.io/mcp` con token Bearer.


Servidor: `chatbot-unab` · protocolo 2025-11-25 · 13 herramientas


## Herramientas expuestas

| herramienta | descripción |
|---|---|
| consultar_estado_matricula | Estado de matrícula del periodo actual y resumen académico del estudiante. |
| avance_plan_estudios | Avance del estudiante en el plan de estudios, semestre por semestre. |
| historial_academico | Historial de calificaciones del estudiante y PGA por periodo. |
| cursos_habilitados | Cursos que el estudiante podrá inscribir el próximo periodo (prerrequisitos y créditos cumplidos). |
| proyeccion_graduacion | Proyección de semestres restantes hasta el grado. |
| alertas_requisitos | Alertas priorizadas: estado académico de riesgo, matrícula pendiente, cursos cuello de botella, |
| competencias_digitales | Estado del estudiante en la Ruta de Competencias Digitales del CCD (requisito de grado): |
| recomendaciones_personalizadas | Recomendaciones personalizadas para el éxito académico basadas en datos. |
| ruta_autoaprendizaje | Ruta de autoaprendizaje personalizada: cómo estudiar y mejorar, con un plan semanal. |
| info_curso | Información de un curso del plan: créditos, semestre, prerrequisitos, cursos que habilita y |
| buscar_documentos_institucionales | Búsqueda RAG híbrida (semántica pgvector + léxica) en documentos institucionales: Reglamento |
| calendario_academico | Fechas del calendario académico: inscripciones, pruebas diagnósticas, inicio de cursos, |
| noticias_recientes | Noticias, convocatorias, nuevos cursos y certificaciones de la UNAB obtenidas por el scraper |


## `consultar_estado_matricula({"codigo": "U00100003"})` · 0.3 s

```json
{
  "periodo_actual": "2026-2",
  "resumen": {
    "codigo": "U00100003",
    "nombre_completo": "Laura Camila Martínez Ardila",
    "email": "laura.martinez003@unab.edu.co",
    "programa_id": "ISIS",
    "programa": "Ingeniería de Sistemas",
    "cohorte": "2022-1",
    "condicion": "Activo",
    "trabaja": false,
    "beca": "Deportiva",
    "periodos_cursados": 10,
    "semestre_por_creditos": 9,
    "creditos_aprobados": 142,
    "creditos_totales": 154,
    "creditos_pendientes": 12,
    "porcentaje_avance": 92.2,
    "cursos_aprobados": 49,
    "total_reprobados": 3,
    "pga_acumulado": 3.78,
    "ultimo_periodo_evaluado": "2026-1",
    "pga_ultimo_periodo": 4.36,
    "estado_academico": "Normal",
    "cursos_en_curso": 1,
    "creditos_en_curso": 12,
    "estado_matricula_actual": "Matriculado",
    "saldo_pendiente": 0.0
  },
  "cursos_matriculados_actuales": [
    {
      "curso_id": "ISIS5901",
      "curso": "Práctica Profesional",
      "creditos": 12
    }
  ],
  "historial_matricula": [
    {
      "periodo_id": "2026-2",
      "estado": "Matriculado",
      "creditos_inscritos": 12,
      "valor_liquidado": 9850000.0,
      "valor_pagado": 9850000.0
    },
    {
      "periodo_id": "2026-1",
      "estado": "Matriculado",
      "creditos_inscritos": 12,
      "valor_liquidado": 9850000.0,
      "valor_pagado": 9850000.0
    },
    {
      "periodo_id": "2025-2",
      "estado": "Matriculado",
      "creditos_inscritos": 16,
      "valor_liquidado": 9850000.0,
      "valor_pagado": 9850000.0
    },
    {
      "periodo_id": "2025-1",
      "estado": "Matricu
… (recortado)
```


## `proyeccion_graduacion({"codigo": "U00100002", "creditos_por_semestre": 16})` · 0.6 s

```json
{
  "plan_completo": true,
  "requisitos_de_grado_pendientes": [
    "Suficiencia en inglés B1",
    "Presentación Saber Pro",
    "Ruta 1 de Competencias Digitales (Competencias Digitales Básicas)",
    "Ruta 3 de Competencias Digitales (Tecnología Transformativa)"
  ],
  "nota": "El periodo proyectado corresponde a TERMINAR LOS CURSOS del plan. Para graduarse también deben cumplirse los requisitos de grado pendientes listados.",
  "estudiante": "Andrés Felipe Gómez Pinzón",
  "creditos_pendientes": 127,
  "supuesto": "Carga máxima 16 créditos/semestre; asume aprobar los cursos actuales.",
  "semestres_restantes_ideal": 9,
  "periodo_grado_ideal": "2031-1",
  "cadena_critica_semestres": 6,
  "plan_sugerido": [
    {
      "periodo": "2027-1",
      "creditos": 16,
      "cursos": [
        "Cálculo Integral (4 cr)",
        "Física Mecánica (4 cr)",
        "Estructuras de Datos (4 cr)",
        "Bases de Datos I (4 cr)"
      ]
    },
    {
      "periodo": "2027-2",
      "creditos": 16,
      "cursos": [
        "Física Electricidad y Magnetismo (4 cr)",
        "Ingeniería de Software I (3 cr)",
        "Análisis y Diseño de Algoritmos (3 cr)",
        "Probabilidad y Estadística (3 cr)",
        "Bases de Datos II (3 cr)"
      ]
    },
    {
      "periodo": "2028-1",
      "creditos": 16,
      "cursos": [
        "Arquitectura de Computadores (3 cr)",
        "Ingeniería de Software II (3 cr)",
        "Ecuaciones Diferenciales (3 cr)",
        "Inglés III (2 cr)",
        "Desarrollo de Aplicaciones Web (3 cr)",
        "Ética y Ciudadanía (2 cr)"
      ]
    },
 
… (recortado)
```


## `recomendaciones_personalizadas({"codigo": "U00100002"})` · 0.2 s

```json
{
  "estudiante": "Andrés Felipe Gómez Pinzón",
  "estado_academico": "En prueba académica",
  "pga_acumulado": 2.95,
  "carga_recomendada_creditos": "12–14",
  "riesgo_academico": {
    "probabilidad": 0.828,
    "nivel": "alto",
    "modelo": "Regresión logística (sklearn) · P(prueba académica en t+1)",
    "intercepto": -1.122,
    "factores": [
      {
        "feature": "pga_acumulado",
        "etiqueta": "PGA acumulado",
        "valor": 2.95,
        "media": 3.5,
        "contribucion": 2.589,
        "efecto": "aumenta"
      },
      {
        "feature": "creditos_por_periodo",
        "etiqueta": "Ritmo de avance (créditos por periodo)",
        "valor": 3.5,
        "media": 12.92,
        "contribucion": -0.776,
        "efecto": "reduce"
      },
      {
        "feature": "pga_ultimo_periodo",
        "etiqueta": "PGA último periodo",
        "valor": 3.09,
        "media": 3.49,
        "contribucion": 0.588,
        "efecto": "aumenta"
      },
      {
        "feature": "trabaja",
        "etiqueta": "Trabaja",
        "valor": 1.0,
        "media": 0.17,
        "contribucion": 0.282,
        "efecto": "aumenta"
      },
      {
        "feature": "reprobados_por_periodo",
        "etiqueta": "Reprobados por periodo",
        "valor": 1.25,
        "media": 1.04,
        "contribucion": 0.013,
        "efecto": "aumenta"
      }
    ],
    "explicacion": "Lo que más eleva tu riesgo: PGA acumulado bajo (2.95 vs 3.50 del programa). Lo que más lo reduce: Ritmo de avance (créditos por periodo) bajo (3.5 vs 12.9 del programa)."
  },
  "recomendaciones": [
   
… (recortado)
```


## `buscar_documentos_institucionales({"pregunta": "requisitos de grado", "k": 2})` · 1.7 s

```json
{
  "pregunta": "requisitos de grado",
  "fragmentos": [
    {
      "fragmento": "Reglamento Estudiantil de Pregrado UNAB (2019) — CAPÍTULO SÉPTIMO. De los grados\nposiciones legales vigentes y los procedimientos acadé-\nmicos, administrativos y financieros de la Universidad, en la fecha establecida \npara tal fin.\n\nARTÍCULO 67. Son requisitos para obtener el título en estudios de pregrado: \na. Tener todas las calificaciones de sus actividades académicas regis-\ntradas y aprobadas en la historia académica institucional. \nb. Acreditar el nivel de inglés exigido en el currículo y certificado por el \nDepartamento de Lenguas de la UNAB o una prueba internacional \navalada por el mismo. \nc. Haber cursado y aprobado las actividades del componente instrumen-\ntal en Informática y Bienestar Universitario definido por la Universidad. \nd. Haber obtenido un Promedio General Acumulado igual o superior a \ntres, punto, dos, cero (3.20) en el programa en que se solicita su titu-\nlación. \ne. Diligenciar y entregar la solicitud de grado en las fechas establecidas \nen el cronograma académico de grados. \nf. No estar siendo investigado dentro de un proceso disciplinario ni en \ncumplimiento de una sanción. \ng. Acreditar los documentos legales y académicos exigidos para la ob-\ntención del respectivo título. Los estudiantes extranjeros deberán pre-\nsentar pasaporte vigente. \nh. Cumplir con los demás requisitos exigidos por cada programa.",
      "titulo": "Reglamento Estudiantil de Pregrado UNAB (2019)",
      "fuente": "https://unab.edu.co/NewFolder/Reglamento-estudiantil-pregr
… (recortado)
```


## Sin token (rechazado)

`POST https://mcp.35-168-41-252.sslip.io/mcp` sin Bearer → HTTP 401
