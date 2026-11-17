# Servidor MCP

El servidor `chatbot-unab` (`mcp_server/server.py`) está construido con **FastMCP** (SDK oficial de Model Context Protocol para Python) y expone 12 herramientas, 1 recurso y 1 prompt. Cualquier cliente MCP (el nodo *MCP Client Tool* de n8n, Claude Desktop, scripts propios) puede descubrirlas y llamarlas dinámicamente. También publica un puente REST para que n8n y la app obtengan datos sin pasar por el protocolo MCP.

## 1. Archivos

| Archivo | Función |
|---|---|
| `server.py` | Definición de herramientas, recurso, prompt, rutas HTTP y autenticación |
| `planner.py` | Planificador de semestres (camino crítico) y simulación Monte Carlo |
| `rag.py` | Recuperación híbrida (semántica + léxica + RRF); ver [rag.md](rag.md) |
| `db.py` | Pool de conexiones psycopg, consultas parametrizadas, validación del código estudiantil |
| `modelo_riesgo.json` | Coeficientes de la regresión logística exportada desde el notebook |
| `test_client.py` | Cliente MCP de prueba (Streamable HTTP) |
| `Dockerfile` | Imagen `python:3.12-slim`, usuario no root, `HEALTHCHECK` sobre `/health` |

## 2. Transporte, rutas y autenticación

| Ruta | Método | Descripción | Auth |
|---|---|---|---|
| `/mcp` | POST | Endpoint MCP, transporte **Streamable HTTP** (`stateless_http=True`, `json_response=True`) | Bearer |
| `/health` | GET | `{"status": "ok", "db": true, "server": "chatbot-unab"}`; `degraded` si la base no responde | Pública |
| `/api/tool/{nombre}` | POST | Puente REST: cuerpo JSON con los argumentos de las 4 herramientas no estudiantiles (`info_curso`, `buscar_documentos_institucionales`, `calendario_academico`, `noticias_recientes`) | Bearer |
| `/api/login` | POST | `{codigo, pin}` → `{ok, estudiante}` o `{ok: false, mensaje}`; usa `academico.verificar_pin` | Bearer |
| `/api/dashboard` | POST | `{codigo, pin}` → tablero completo para la app (una sola llamada) | Bearer |

Los datos de un estudiante solo se consultan por `/api/login` y `/api/dashboard`, que verifican código y PIN en cada llamada. El puente `/api/tool/{nombre}` no expone herramientas de estudiante.

**Autenticación:** un middleware exige `Authorization: Bearer <token>` en toda ruta que empiece por `/mcp` o `/api`; si falta responde `401 {"error": "unauthorized"}`. La variable `MCP_AUTH_TOKEN` es obligatoria: el servidor no arranca sin ella (falla cerrada) y compara el token en tiempo constante.

**Validación:** todo código estudiantil debe cumplir `^U\d{8}$` (se normaliza a mayúsculas); si no, la herramienta devuelve un error claro. Todas las consultas son parametrizadas y se ejecutan con el rol `mcp_readonly`.

**Variables de entorno:** `MCP_DATABASE_URL` (obligatoria, con el rol de solo lectura, salvo que se defina `MCP_ALLOW_OWNER_DB=1`), `MCP_AUTH_TOKEN` (obligatoria), `GEMINI_API_KEY`, `GEMINI_EMBED_MODEL`, `CALENDAR_SHEET_CSV_URL`, `MCP_HOST`, `MCP_PORT`, `DB_POOL_MAX`.

## 3. Herramientas

Todas las herramientas de estudiante reciben `codigo` (ejemplo: `U00100001`).

### Estado y avance

| Herramienta | Argumentos | Devuelve | Vista/fuente |
|---|---|---|---|
| `consultar_estado_matricula` | `codigo` | Periodo actual, resumen 360° (créditos, avance, PGA, estado académico, matrícula, saldo), cursos matriculados y últimos 4 periodos de matrícula | `v_estudiante_resumen`, `matricula`, `v_historial_academico` |
| `avance_plan_estudios` | `codigo` | Semestre por semestre: cursos con estado y nota, créditos aprobados/totales; avance por componente | `v_avance_plan` |
| `historial_academico` | `codigo`, `periodo` (opcional, ej. `2025-2`) | Cursos con nota e intento, y PGA por periodo con estado académico | `v_historial_academico`, `v_pga_periodo` |
| `cursos_habilitados` | `codigo`, `asumir_aprobados_actuales` (por defecto `true`) | Cursos que puede inscribir el próximo periodo, con tasa de reprobación y cuántos cursos bloquea; repitencias primero | `curso`, `prerrequisito`, `v_estadistica_curso` |
| `proyeccion_graduacion` | `codigo`, `creditos_por_semestre` (10–20, por defecto 18), `incluir_cursos_actuales` | Plan semestre a semestre (`plan_completo`), periodo de grado ideal, cadena crítica, `requisitos_de_grado_pendientes`, proyección probabilística (P50 y P90) y una nota: el periodo proyectado corresponde a terminar los cursos | `planner.py` |
| `alertas_requisitos` | `codigo` | Alertas priorizadas (ALTA, MEDIA, BAJA, INFO) y requisitos de grado | `v_alertas` |
| `competencias_digitales` | `codigo` | Estado de las 3 rutas del CCD, prueba diagnóstica, `insignia_lista`, oferta para las rutas pendientes | `v_competencias_digitales` |
| `recomendaciones_personalizadas` | `codigo` | Carga recomendada, riesgo estimado y lista de recomendaciones | Reglas + modelo de riesgo |

### Información institucional

| Herramienta | Argumentos | Devuelve |
|---|---|---|
| `info_curso` | `nombre_o_codigo` (ej. `ISIS2303` o "estructuras de datos"; insensible a tildes) | Créditos, semestre, prerrequisitos, cursos que habilita, nota promedio, tasa de reprobación |
| `buscar_documentos_institucionales` | `pregunta`, `k` (1–8, por defecto 5) | Fragmentos con título, fuente y puntajes, más la instrucción de citar |
| `calendario_academico` | `categoria` (opcional), `solo_proximos` (por defecto `true`) | Hasta 25 eventos; fuente Google Sheets (CSV) o, si falla, `chatbot.calendario` |
| `noticias_recientes` | `tema` (opcional), `limite` (1–10, por defecto 5) | Noticias; con tema usa búsqueda de texto completo, sin tema ordena por relevancia |

### Ejemplos

Llamada MCP (con `test_client.py` o un cliente propio):

```json
{"name": "proyeccion_graduacion", "arguments": {"codigo": "U00100001", "creditos_por_semestre": 18}}
```

Respuesta (abreviada y con valores ilustrativos; los reales dependen de los datos):

```json
{
  "estudiante": "Valentina Rojas Duarte",
  "creditos_pendientes": 68,
  "semestres_restantes_ideal": 4,
  "periodo_grado_ideal": "2028-2",
  "plan_sugerido": [{"periodo": "2027-1", "creditos": 18, "cursos": ["Sistemas Operativos (3 cr)", "..."]}],
  "proyeccion_probabilistica": {
    "semestres_p50": 4, "semestres_p90": 5,
    "periodo_grado_p50": "2028-2", "periodo_grado_p90": "2029-1",
    "cursos_con_mayor_riesgo_de_reprobar": [{"curso": "Cálculo Integral", "prob_reprobar": 0.1}],
    "metodo": "Monte Carlo, 400 simulaciones, p(aprobar)=σ(logit(1−tasa_rep)+1.9·(PGA−3.55))"
  }
}
```

Mismo llamado por el puente REST:

```bash
curl -X POST https://mcp.35-168-41-252.sslip.io/api/tool/info_curso \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre_o_codigo": "estructuras de datos"}'
```

Un nombre de herramienta desconocido responde `404`; argumentos inválidos (por ejemplo un código mal formado) responden `400` con el mensaje.

> **Nota sobre tipos de parámetros.** Los parámetros opcionales son cadenas de texto con valor por defecto `""` (no `null`), porque Gemini rechaza tipos anulables en las declaraciones de función.

## 4. Recurso, prompt y tablero

- **Recurso** `unab://plan-de-estudios`: el plan completo (curso, créditos, semestre, componente) en JSON.
- **Prompt** `asesor_academico(codigo)`: instrucciones para que el modelo genere un informe de consejería (matrícula, avance, alertas, proyección y recomendaciones) en español.
- **`/api/dashboard`**: devuelve en una llamada `resumen`, `alertas`, `competencias`, `avance` (por semestre), `proyeccion`, `riesgo`, `noticias` (8) y `calendario` (12 eventos próximos). Si la proyección falla, devuelve `null` en ese campo y el resto continúa. Es la fuente de la pantalla de inicio de la app.

## 5. Planificador de semestres (`planner.py`)

Se modela el plan como un grafo dirigido acíclico (DAG) de prerrequisitos.

**Camino crítico.** Para cada curso pendiente, `camino_critico` calcula la longitud de la cadena más larga de cursos que dependen de él: `prof(c) = 1 + max(prof(h))` sobre sus cursos hijos (los que lo exigen). Un curso con valor alto retrasa la graduación si se aplaza.

**Programación por listas (list scheduling).** En cada semestre simulado:

1. Se toman los cursos pendientes **habilitados** (todos los prerrequisitos aprobados y créditos mínimos cumplidos).
2. Se ordenan por camino crítico descendente, luego por semestre sugerido y luego por tasa de reprobación descendente.
3. Se agregan al semestre en ese orden mientras no se supere el tope de créditos.
4. La práctica profesional (`ISIS5901`) solo se programa cuando es el último curso pendiente.
5. Se marcan como aprobados y se repite hasta no tener cursos pendientes (máximo 20 semestres). Si no se puede programar nada, se detiene para evitar bucles infinitos.

El resultado determinista es el `plan_sugerido`; su longitud es `semestres_restantes_ideal`.

**Simulación Monte Carlo.** Se repite el mismo planificador **400 veces** (semilla fija 7 para que sea reproducible) y en cada repetición cada curso programado se aprueba con probabilidad

$$
p = \sigma\big(\operatorname{logit}(1-\text{tasa\_rep}) + 1.9\,(\text{PGA}-3.55)\big),\qquad p \in [0.35,\,0.99]
$$

donde `tasa_rep` es la tasa histórica de reprobación del curso (0–1; si no hay datos se usa 15 %), `PGA` es el acumulado del estudiante (3.55 si no existe) y 3.55 es la nota media simulada. Un estudiante con PGA alto aprueba con más probabilidad que el promedio del curso y uno con PGA bajo con menos. Los cursos reprobados vuelven a quedar pendientes y se reprograman en el siguiente semestre.

Las simulaciones que no terminan dentro del límite cuentan como el máximo (24 semestres) y se reportan en `simulaciones_incompletas`. Con las 400 duraciones (en semestres) se reportan el **P50** (periodo de grado probable), el **P90** (escenario pesimista), el promedio y los 5 cursos con mayor probabilidad de reprobar (`1 − p`). El periodo de grado se obtiene sumando esos semestres al periodo actual con `siguiente_periodo`.

## 6. Modelo de riesgo académico

La herramienta `recomendaciones_personalizadas` (y el campo `riesgo` del tablero) estima la **probabilidad de quedar en prueba académica en el siguiente periodo**.

- **Entrenamiento:** `notebooks/01_eda_y_modelo_riesgo.ipynb` (generado por `notebooks/build_notebook.py`). Unidad de análisis: estudiante-periodo; etiqueta: en prueba académica en *t+1* con la información del cierre de *t*. Partición **agrupada por estudiante** (`GroupShuffleSplit`, 25 % de prueba) para evitar fuga de información. Se compara con un Random Forest y se elige la regresión logística por rendimiento comparable y mejor calibración.
- **Variables:** `pga_acumulado`, `pga_ultimo_periodo`, `reprobados_por_periodo`, `creditos_por_periodo`, `trabaja`.
- **Métricas en el conjunto de prueba:** AUC 0.854, Brier 0.148 (770 observaciones de entrenamiento). Son métricas sobre **datos sintéticos**.
- **Inferencia en el servidor:** se leen los coeficientes de `modelo_riesgo.json`, se estandarizan las variables con las medias y desviaciones guardadas y se calcula `p = σ(intercepto + Σ coef·z)`. Nivel: `alto` si p ≥ 0.5, `medio` si p ≥ 0.25, `bajo` en otro caso.

Las recomendaciones combinan ese riesgo con reglas explícitas: carga de 12–14 créditos en prueba académica, 14–16 si es condicional o riesgo alto, 12–15 si trabaja; aviso de cursos exigentes habilitados (tasa de reprobación ≥ 25 %); cuellos de botella; rutas del CCD pendientes (se sugiere Interacción Digital, Analítica Digital o IA Generativa); y fortalezas cuando hay notas de 4.3 o más.

## 7. Cómo conectarse

### Desde n8n (nodo MCP Client Tool)

- Endpoint: `http://mcp-server:9000/mcp` dentro de la red de Docker (variable `MCP_URL`) o `https://mcp.35-168-41-252.sslip.io/mcp` desde fuera.
- Transporte: **HTTP Streamable**.
- Autenticación: *Bearer* con el valor de `MCP_AUTH_TOKEN`.
- Herramientas: todas, o la selección que necesite el agente.

### Desde Claude (remoto, HTTP Streamable) — probado

Claude Code se conecta al servidor desplegado en AWS por internet, sin copiar el código. Archivo `mcp.json` (no lo subas; lleva el token):

```json
{
  "mcpServers": {
    "chatbot-unab": {
      "type": "http",
      "url": "https://mcp.35-168-41-252.sslip.io/mcp",
      "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

```bash
claude -p "Usa consultar_estado_matricula para U00100003 y resume su estado" \
  --mcp-config mcp.json --strict-mcp-config \
  --allowedTools "mcp__chatbot-unab__consultar_estado_matricula"
```

Resultado real (17-nov-2026): Claude descubrió la herramienta, la llamó y respondió «Estado académico: Normal · PGA 3.78 · 142 de 154 créditos aprobados (92.2 %)». También funciona con `claude mcp add --transport http chatbot-unab https://mcp.35-168-41-252.sslip.io/mcp --header "Authorization: Bearer <token>"` o en Claude Desktop como conector personalizado.

### Desde OpenAI (Responses API, herramienta `mcp` remota)

El mismo endpoint sirve a modelos de OpenAI. Este fragmento sigue el formato documentado por OpenAI; no se ejecutó en el proyecto por no contar con una API key de OpenAI:

```python
from openai import OpenAI

r = OpenAI().responses.create(
    model="gpt-4.1-mini",
    tools=[{
        "type": "mcp",
        "server_label": "chatbot-unab",
        "server_url": "https://mcp.35-168-41-252.sslip.io/mcp",
        "headers": {"Authorization": "Bearer <MCP_AUTH_TOKEN>"},
        "require_approval": "never",
    }],
    input="¿Cuántos créditos le faltan a U00100003 para graduarse?",
)
print(r.output_text)
```

### Desde Claude Desktop (stdio, local)

Ejecuta el servidor como subproceso. Añade a `claude_desktop_config.json` (rutas y credenciales de ejemplo; usa las tuyas y no las subas al repositorio):

```json
{
  "mcpServers": {
    "chatbot-unab": {
      "command": "python",
      "args": ["C:/ruta/al/repo/mcp_server/server.py", "--stdio"],
      "env": {
        "MCP_DATABASE_URL": "postgresql://mcp_readonly.<project_ref>:<MCP_DB_PASSWORD>@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
        "GEMINI_API_KEY": "<tu-api-key>"
      }
    }
  }
}
```

En modo `--stdio` no hay servidor HTTP ni autenticación Bearer. El servidor también lee el `.env` de la raíz del repositorio si existe.

### Con el cliente de prueba

```bash
python mcp_server/test_client.py https://mcp.35-168-41-252.sslip.io/mcp U00100001
```

Lee `MCP_AUTH_TOKEN` del `.env`, abre una sesión Streamable HTTP, lista las herramientas y ejecuta `consultar_estado_matricula`, `alertas_requisitos` y `proyeccion_graduacion` mostrando los primeros 600 caracteres de cada respuesta.

### Ejecución local y en contenedor

```bash
python mcp_server/server.py              # http://localhost:9000/mcp
docker compose up -d --build mcp-server  # imagen del Dockerfile, puerto 9000
curl http://localhost:9000/health
```
