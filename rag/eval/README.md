# Evaluación de recuperación del RAG

- `golden.jsonl`: 40 preguntas con documento esperado (`archivo_esperado`), frase de evidencia y categoría.
- `resultados.json`: salida vigente de `rag/evaluate.py` (hit@1/3/5 y MRR@10 por método, categoría y pregunta; `peso_lexico` usado en `hibrido`; `barrido_peso_lexico` si se ejecutó con `--barrido`).
- `resultados_v1_lexico_and.json`: corrida histórica (v1) con el léxico en AND, conservada para el registro de iteraciones.

Ejecutar desde la raíz del proyecto (necesita `DATABASE_URL` y `GEMINI_API_KEY` en `.env`):

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python rag/evaluate.py --barrido
# opciones: --w-lex FLOAT (peso léxico en RRF; defecto env RRF_PESO_LEXICO o 0.0), --barrido, --k 5
```

Peso léxico elegido: 0,0 (mejor MRR en el barrido; elegido con las mismas 40 preguntas, sin conjunto de validación). El canal léxico se mantiene como respaldo; el peso se ajusta con `RRF_PESO_LEXICO` en `mcp_server/rag.py`.

Metodología, iteraciones v1/v2/v3, resultados y limitaciones: [`docs/evaluacion_rag.md`](../../docs/evaluacion_rag.md).

Para agregar preguntas, añade una línea JSON a `golden.jsonl` con las claves `id`, `pregunta`, `archivo_esperado`, `evidencia`, `categoria`, y comprueba que la `evidencia` exista literalmente en el archivo.
