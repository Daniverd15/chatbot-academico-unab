# Evaluación de la recuperación del RAG

Este documento describe cómo se mide la calidad de la **recuperación** (retrieval) del RAG institucional y presenta los resultados reales obtenidos contra la base de datos en vivo (Supabase, pgvector), junto con el registro de las iteraciones que se hicieron sobre el canal léxico y la fusión. No se evalúa la redacción de la respuesta final del LLM, solo si los fragmentos correctos llegan al contexto.

## Metodología

- **Conjunto dorado** (`rag/eval/golden.jsonl`): 40 preguntas de estudiantes en español, con variedad de registro (formal, coloquial, sin tildes, sin signos de interrogación). Cada una tiene un único documento esperado entre los 16 de `rag/corpus/md`, una frase literal de ese documento que contiene la respuesta (`evidencia`) y una categoría. Las frases de evidencia se verificaron automáticamente contra el texto de cada archivo.
- **Distribución**: reglamento 18, competencias digitales 10, plan de estudios 6, noticias 6 (total 40). Las preguntas del reglamento cubren estados académicos (art. 24), matrícula, reserva de cupo, cancelaciones, evaluación (habilitación, validación, revisión de notas, inasistencia), créditos, grados y programas de apoyo. Las de competencias digitales cubren umbral de 70 %, homologación, pruebas de primer ingreso (virtual y presencial), cursos vacacionales e insignias.
- **Tres métodos**, implementados en `rag/evaluate.py` con las mismas consultas SQL que el servidor MCP:
  - *Semántico*: embedding de la pregunta con `gemini-embedding-001` (`RETRIEVAL_QUERY`) y `chatbot.match_documentos` (coseno).
  - *Léxico*: `chatbot.buscar_texto` (`tsvector` en español; la definición cambió entre v1 y v2, ver abajo).
  - *Híbrido*: Reciprocal Rank Fusion (k = 60) de las dos listas de 20 resultados, con peso 1,0 para la lista semántica y un peso `w_lex` para la léxica (en v1 y v2, w_lex = 1,0; es decir, RRF clásico).
- **Relevancia a nivel de documento**: un fragmento cuenta como acierto si `metadata->>'archivo'` coincide con el archivo esperado. Las filas del scraper de noticias (`origen='noticia'`, sin `archivo`) cuentan solo si su `url` coincide con la del front-matter del archivo esperado.
- Se recuperan los 10 mejores fragmentos por método y se registra la posición del primer acierto (o `null` si no aparece).

## Métricas

- **hit@k**: proporción de preguntas cuyo primer fragmento relevante está en las primeras *k* posiciones (k = 1, 3, 5).
- **MRR@10** (Mean Reciprocal Rank): promedio de 1/posición del primer fragmento relevante; vale 0 si no aparece en el top 10.

## Registro de iteraciones

Todas las corridas usan las mismas 40 preguntas. La salida de v1 se conserva en `rag/eval/resultados_v1_lexico_and.json`; `rag/eval/resultados.json` contiene la corrida vigente (v3).

### v1: léxico con AND

`buscar_texto` usaba `websearch_to_tsquery`, que exige que **todos** los términos de la pregunta estén en el mismo fragmento.

| Método    | hit@1 | hit@3 | hit@5 | MRR@10 |
|-----------|------:|------:|------:|-------:|
| Semántico | 0,950 | 1,000 | 1,000 |  0,975 |
| Léxico    | 0,100 | 0,100 | 0,100 |  0,100 |
| Híbrido (pesos iguales) | 0,975 | 1,000 | 1,000 | 0,988 |

Lo aprendido: con preguntas largas y coloquiales el AND casi nunca encuentra un fragmento que contenga todas las palabras, así que el léxico devolvía cero filas (solo acertó en 4 de 40). El híbrido parecía bueno (0,975) pero era el semántico haciendo casi todo el trabajo; el canal léxico no aportaba.

### v2: léxico con OR (ts_rank_cd), híbrido con pesos iguales

Se cambió `buscar_texto` para unir los lexemas de la consulta con OR y ordenar con `ts_rank_cd`.

| Método    | hit@1 | hit@3 | hit@5 | MRR@10 |
|-----------|------:|------:|------:|-------:|
| Semántico | 0,950 | 1,000 | 1,000 |  0,975 |
| Léxico    | 0,650 | 0,850 | 0,875 |  0,760 |
| Híbrido (w_lex = 1,0) | 0,925 | 0,950 | 1,000 | 0,949 |

Lo aprendido: el léxico pasó de 0,10 a 0,65 en hit@1, pero el híbrido con pesos iguales **empeoró** y quedó por debajo del semántico solo (0,925 frente a 0,950). Un canal léxico más ruidoso (OR devuelve muchos fragmentos con palabras comunes como "cuántos", "estudiante" o "créditos") puede arrastrar al fragmento equivocado cuando la fusión le da el mismo peso que al semántico. Por categoría, el léxico es especialmente flojo en reglamento (hit@1 0,61, el documento tiene cientos de fragmentos con vocabulario repetido) y en noticias (0,33).

### v3: RRF ponderado (barrido del peso léxico)

Se añadió el parámetro `w_lex` (peso de la lista léxica; semántico fijo en 1,0). El barrido reutiliza las mismas listas recuperadas (`python rag/evaluate.py --barrido`), con la corrida del 2026-11-17:

| w_lex | hit@1 | hit@3 | hit@5 | MRR@10 |
|------:|------:|------:|------:|-------:|
| 0,00 (solo semántico en la fusión) | 0,950 | 1,000 | 1,000 | 0,975 |
| 0,25  | 0,900 | 0,975 | 1,000 | 0,944 |
| 0,50  | 0,900 | 0,950 | 1,000 | 0,936 |
| 0,75  | 0,925 | 0,950 | 1,000 | 0,949 |
| 1,00 (RRF clásico) | 0,925 | 0,950 | 1,000 | 0,949 |

**Regla de elección** (fijada antes de mirar la tabla): el peso con mejor MRR@10; en caso de empate, el mayor peso léxico que sea ≤ 0,5. El mejor MRR es el de `w_lex = 0,0` (0,975), sin empate, así que **el peso elegido es 0,0**: en el conjunto dorado, ningún peso léxico positivo mejora al semántico. Dicho sin rodeos: el mejor sistema de este experimento es, en términos de ranking, **recuperación semántica pura**. El híbrido con w_lex = 0 (hit@1 0,950, MRR 0,975) es idéntico al semántico.

Lo aprendido y advertencias:

- **El peso se eligió con las mismas 40 preguntas con las que se evalúa** (no hay conjunto de validación separado). Cualquier "mejora" de una configuración sobre otra está sesgada hacia lo optimista; aquí, además, la conclusión es conservadora (no se encontró ninguna ganancia), y diferencias de una o dos preguntas (2,5 a 5 puntos de hit@1) no son estadísticamente concluyentes. La no monotonía de la tabla (0,5 peor que 0,75) es ruido de muestra pequeña, no una tendencia real.
- Con el léxico en OR, hay preguntas donde el léxico acierta y el semántico no (q25 sobre en qué semestres terminar las rutas, y q37 sobre los vacacionales de inglés de fin de año: léxico en posición 1, semántico en posición 2), pero con w_lex = 0 la fusión no puede aprovecharlas, y con pesos mayores se pierden más aciertos de los que se ganan (el léxico en OR suele poner el documento correcto en posiciones 2 a 6 en las preguntas del reglamento, y esas listas ruidosas desplazan al acierto del semántico).

### Por qué se mantiene el canal léxico aunque su peso sea 0

Con `RRF_PESO_LEXICO = 0.0` el canal léxico no altera el orden cuando el semántico responde, pero se conserva en `mcp_server/rag.py` por razones que este conjunto dorado no mide:

1. **Respaldo si falla el embedding**: si la API de Gemini falla o agota la cuota gratuita, `buscar()` captura el error y la lista semántica queda vacía; entonces el ranking lo decide solo el canal léxico (0,65 de hit@1 en v2, frente a 0,10 en v1), en lugar de devolver nada.
2. **Términos exactos**: códigos de curso (ISIS3603), números de artículo o siglas son el caso en que un índice léxico suele superar a los embeddings; el conjunto dorado tiene pocas preguntas así, por lo que su beneficio no aparece en las métricas.
3. **Ajuste sin cambiar código**: el peso se puede subir con la variable de entorno `RRF_PESO_LEXICO` (el valor por defecto es 0,0) si se amplía el conjunto de evaluación y los datos lo justifican.

Un trabajo futuro razonable es medir el híbrido con un conjunto más grande y con preguntas de términos exactos antes de subir el peso.

## Limitaciones

- Conjunto pequeño (40 preguntas) escrito por el propio equipo, que conoce el corpus: puede sobreestimar el rendimiento frente a preguntas reales de estudiantes. Con n = 40, una pregunta mueve hit@1 en 2,5 puntos.
- El peso léxico se seleccionó sobre el mismo conjunto en que se reporta (sin conjunto de validación): las cifras de v3 son optimistas.
- La relevancia es a nivel de **documento**, no de fragmento: un acierto no garantiza que el fragmento recuperado contenga la respuesta (el reglamento tiene cientos de fragmentos). Tampoco se mide la calidad de la respuesta generada ni el rechazo de preguntas fuera de corpus.
- Cada pregunta tiene un solo documento válido; documentos casi duplicados (p. ej. los dos avisos de cursos vacacionales de inglés, que comparten estructura y precio) hacen ambiguo el resultado y explican las posiciones 2 de q25 y q37 en el semántico.
- Pocas preguntas con términos exactos (códigos, artículos), justo el caso donde se espera que el canal léxico aporte.

## Cómo reproducir

```bash
# requiere DATABASE_URL y GEMINI_API_KEY en .env (y la ingesta ya ejecutada)
PYTHONIOENCODING=utf-8 .venv/Scripts/python rag/evaluate.py --barrido    # Windows
python rag/evaluate.py --barrido --w-lex 0.0                              # Linux/macOS
```

Opciones: `--w-lex FLOAT` (peso léxico del campo `hibrido`; por defecto lee `RRF_PESO_LEXICO` y, si no existe, 0,0), `--barrido` (tabla para w_lex en 0, 0,25, 0,5, 0,75 y 1,0, guardada en `barrido_peso_lexico`) y `--k` (solo para el resumen en consola). El script embebe las preguntas en un lote (con reintentos ante 429), imprime las tablas y reescribe `rag/eval/resultados.json`. Los resultados pueden variar levemente si cambia el corpus o el modelo de embeddings.
