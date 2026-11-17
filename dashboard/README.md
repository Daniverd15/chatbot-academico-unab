# Observatorio académico UNABot

Tablero analítico (Streamlit + Plotly) del proyecto *Chatbot de apoyo académico — Ingeniería de Sistemas UNAB*.
Lee en modo **solo lectura** la base PostgreSQL (Supabase) que simula Banner/COSMOS y la bitácora del chatbot.

> Datos sintéticos — simulación Banner/COSMOS.

## Páginas

| # | Página | Contenido |
|---|--------|-----------|
| 1 | Panorama del programa | KPIs (activos, PGA promedio, % prueba, % condicional, deserción), estado académico, condición por cohorte, embudo de avance por créditos, distribución del PGA con umbrales 3,00 / 3,20 (Reglamento 2019, art. 24), evolución por periodo |
| 2 | Cursos y cuellos de botella | Heatmap de reprobación curso × periodo, nota promedio vs. reprobación (tamaño = cursos bloqueados), top 10 cuellos de botella, grafo de prerrequisitos por semestre con resaltado de cadena |
| 3 | Riesgo académico | Modelo logístico `modelo_riesgo.json` aplicado a los activos (misma función que `_riesgo_academico` del servidor MCP): distribución, riesgo por cohorte / trabajo / beca, top de riesgo con nombres enmascarados, coeficientes, AUC y Brier |
| 4 | Competencias digitales | Cumplimiento por ruta, % insignia lista, prueba diagnóstica (umbral 70), cursos del CCD más tomados, insignia por cohorte |
| 5 | Uso del chatbot | Conversaciones por día, intenciones, latencia p50/p95 y por intención, guardrails, calificaciones, últimas 20 preguntas (código enmascarado) |
| 6 | Calidad del RAG | Métricas de `rag/eval/resultados.json` (Hit@k, MRR por método, barrido del peso léxico, MRR por categoría, detalle por pregunta) y estadísticas del corpus de `chatbot.rag_documentos` |
| 7 | Noticias | Noticias del scraper por tipo y mes, relevancia en el tiempo y las más relevantes |

## Estructura

```
dashboard/
├── app.py                 # entrada: configuración, estilos y st.navigation
├── vistas/                # una página por archivo
├── lib/
│   ├── db.py              # conexión psycopg 3 cacheada + st.cache_data(ttl=300)
│   ├── datos.py           # consultas SQL (agregadas, sin SELECT * sobre estudiante)
│   ├── riesgo.py          # modelo logístico vectorizado
│   └── ui.py              # paleta UNAB, plantilla Plotly, CSS, tarjetas KPI
├── static/logo.svg
├── .streamlit/config.toml # tema
├── requirements.txt
└── Dockerfile
```

## Configuración

| Variable | Uso |
|----------|-----|
| `DASH_DATABASE_URL` | Cadena de conexión del rol de solo lectura (preferida) |
| `MCP_DATABASE_URL` | Respaldo si no existe la anterior (rol `mcp_readonly`) |
| `DASH_MODELO_RIESGO` | (Opcional) ruta al `modelo_riesgo.json` |
| `DASH_RAG_EVAL` | (Opcional) ruta al `resultados.json` de la evaluación del RAG |

En local se carga automáticamente el `.env` de la raíz del repositorio.
El modelo se busca en `DASH_MODELO_RIESGO`, `dashboard/modelo_riesgo.json` (= `/app/modelo_riesgo.json` en Docker)
y `../mcp_server/modelo_riesgo.json`. La evaluación del RAG en `DASH_RAG_EVAL`, `../rag/eval/resultados.json`
y `/app/rag_eval/resultados.json`.

## Ejecutar en local

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r dashboard/requirements.txt   # Windows (Linux/macOS: .venv/bin/python)
.venv/Scripts/python -m streamlit run dashboard/app.py
```

Abrir <http://localhost:8501>.

## Docker

El contexto de construcción es `dashboard/`:

```bash
docker build -t unabot-dashboard dashboard
docker run --rm -p 8501:8501 \
  -e DASH_DATABASE_URL="$DASH_DATABASE_URL" \
  -v "$PWD/mcp_server/modelo_riesgo.json:/app/modelo_riesgo.json:ro" \
  -v "$PWD/rag/eval:/app/rag_eval:ro" \
  unabot-dashboard
```

La imagen usa `python:3.12-slim`, corre como usuario sin privilegios y expone el puerto 8501 con healthcheck en
`/_stcore/health`.

## Notas de diseño

- **Privacidad:** `academico.estudiante` solo se consulta por columnas autorizadas; los nombres se enmascaran en SQL
  (`A*** G***`) y los códigos de la bitácora se muestran como `U00****23`. No se lee el texto de las respuestas del
  chatbot ni la columna `embedding`.
- **Rendimiento:** `statement_timeout` es de 8 s; todas las consultas agregan en el servidor y se cachean 5 minutos.
  El botón *Actualizar datos* limpia la caché.
- **Prueba de humo:** `streamlit.testing.v1.AppTest` sobre `app.py` y cada archivo de `vistas/`
  (`AppTest.from_file(...).run(timeout=120)` sin excepciones ni `st.error`).
