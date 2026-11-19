# Evidencia: recuperación del RAG

Generado el 2026-11-19 17:17 con `python scripts/evidencias/generar_evidencias.py rag`.

Cada consulta se convierte en embedding con `gemini-embedding-001` (3072 d, `RETRIEVAL_QUERY`), se busca por coseno en pgvector (índice HNSW sobre `halfvec`) y se fusiona con la búsqueda léxica por RRF (`mcp_server/rag.py`). Se muestran los 3 primeros fragmentos recuperados de los documentos institucionales.


## Reglamento: «¿Qué pasa si quedo en prueba académica y cuál es el promedio mínimo?»

Tiempo de recuperación: 2.55 s

| # | documento | similitud | fragmento |
|---|---|---|---|
| 1 | Reglamento Estudiantil de Pregrado UNAB (2019) | 0.794 | CAPÍTULO PRIMERO: De la admisión y matrícula studiantes en estado académico condicional deberán acogerse al Pro- grama de Acompañamiento y Apoyo Académico establecido en el presente re- glamento. ARTÍCULO 11. Del estudiante en pru… |
| 2 | Reglamento Estudiantil de Pregrado UNAB (2019) | 0.755 | CAPÍTULO PRIMERO: Del acompañamiento y apoyo académicos ecidas por Bienestar Universitario, y sólo podrán matricular hasta tres (3) cursos de su plan de estudios en el siguiente periodo académico regular. Parágrafo 1. El estudiant… |
| 3 | Reglamento Estudiantil de Pregrado UNAB (2019) | 0.733 | CAPÍTULO PRIMERO: Del acompañamiento y apoyo académicos artículo 12 de este reglamento. Parágrafo 3. Cada programa, junto con Bienestar Universitario, realizará el con- trol y seguimiento de estos casos. ARTÍCULO 86. Para solicita… |


## Competencias digitales: «¿Qué es la insignia de competencias digitales y cómo la obtengo?»

Tiempo de recuperación: 0.99 s

| # | documento | similitud | fragmento |
|---|---|---|---|
| 1 | Estudiante UNAB, solicita tu insignia digital | 0.736 | ¿Dónde y cómo solicitarla? La Oficina de Relaciones Nacionales e Internacionales es el área encargada de validar las evidencias presentadas y otorgar las insignias. Con 60 puntos puedes conseguir la de Navegante Intercultural y co… |
| 2 | Así funciona la formación en Competencias Digitales de la UNAB | 0.734 | La oferta en la UNAB - Ruta 1 – Competencias Digitales Básicas (obligatoria para todos): Interacción Digital. Enseña a moverse con seguridad en internet, verificar fuentes y proteger la información. - Ruta 2 – Analítica y Contenid… |
| 3 | Así funciona la formación en Competencias Digitales de la UNAB | 0.727 | Así funciona la formación en Competencias Digitales de la UNAB El Centro de Competencias Digitales presenta su oferta académica. Está organizada en tres rutas de formación que todos los estudiantes de la Universidad UNAB deben com… |


## Plan de estudios: «¿Cuáles son los prerrequisitos de Estructuras de Datos?»

Tiempo de recuperación: 0.96 s

| # | documento | similitud | fragmento |
|---|---|---|---|
| 1 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.688 | Semestre 3 (20 créditos) - Cálculo Multivariable (ISIS2301): 3 créditos, componente Básico, área Matemáticas. Prerrequisitos: Cálculo Integral. - Ecuaciones Diferenciales (ISIS2302): 3 créditos, componente Básico, área Matemáticas… |
| 2 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.67 | Semestre 4 (17 créditos) - Probabilidad y Estadística (ISIS2401): 3 créditos, componente Básico, área Matemáticas. Prerrequisitos: Cálculo Integral. - Análisis y Diseño de Algoritmos (ISIS2402): 3 créditos, componente Específico, … |
| 3 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.67 | Semestre 6 (18 créditos) - Redes de Computadores (ISIS3601): 3 créditos, componente Específico, área Infraestructura. Prerrequisitos: Sistemas Operativos. - Ciencia de Datos (ISIS3602): 3 créditos, componente Específico, área Dato… |


## Requisitos de grado: «¿Qué requisitos necesito para graduarme de Ingeniería de Sistemas?»

Tiempo de recuperación: 0.96 s

| # | documento | similitud | fragmento |
|---|---|---|---|
| 1 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.762 | Requisitos de grado - Ruta de Competencias Digitales: Aprobar un curso de cada una de las tres rutas del Centro de Competencias Digitales (CCD). - Suficiencia en inglés B1: Acreditar nivel B1 (MCER) mediante prueba institucional o… |
| 2 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.748 | Semestre 8 (14 créditos) - Proyecto de Grado (ISIS4801): 4 créditos, componente Específico, área Investigación. Prerrequisitos: Seminario de Investigación. - Gobierno y Arquitectura Empresarial de TI (ISIS4802): 3 créditos, compon… |
| 3 | Plan de estudios de Ingeniería de Sistemas (simulado) | 0.736 | Plan de estudios de Ingeniería de Sistemas (simulado) Programa: Ingeniería de Sistemas — Facultad de Ingeniería. Código SNIES 1643. Modalidad Presencial. Duración: 8 semestres académicos más un semestre de práctica profesional. To… |


## Homologación: «Ya cursé informática, ¿puedo homologar rutas de competencias digitales?»

Tiempo de recuperación: 0.95 s

| # | documento | similitud | fragmento |
|---|---|---|---|
| 1 | Estudiantes UNAB que ya cursaron Informática podrían homologar sus rutas de Competencias Digitales | 0.822 | Cómo funciona la equivalencia - Ruta 1 – Competencias Digitales Básicas (Interacción Digital): la tiene homologada quien aprobó Cultura Digital y Vida en Línea. En planes de Informática más antiguos, también quien aprobó Internet … |
| 2 | Estudiantes UNAB que ya cursaron Informática podrían homologar sus rutas de Competencias Digitales | 0.806 | Contacto Si tienes dudas sobre un caso puntual, escribe a ccdigital@unab.edu.co o llama al (607) 643 6111, ext. 1807 / 1644.… |
| 3 | Estudiantes UNAB que ya cursaron Informática podrían homologar sus rutas de Competencias Digitales | 0.798 | ¿Cómo se verifica? Directores de programa, consejeros y personal administrativo UNAB pueden revisar el historial académico del estudiante en Banner, en las formas SHATERM y SOATEST. Si aparece aprobada alguna de las materias anter… |
