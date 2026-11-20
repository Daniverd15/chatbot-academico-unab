# Evidencia: base de datos PostgreSQL (Supabase)

Generado el 2026-11-19 20:47 con `python scripts/evidencias/generar_evidencias.py bd`, conectado al servidor de Supabase (PostgreSQL 17 + pgvector).


Servidor: `PostgreSQL 17.11 on x86_64-pc-linux-gnu, compiled by gcc (GC…`


## Tablas y número de filas

| tabla | filas |
|---|---|
| academico.cd_curso | 11 |
| academico.cd_inscripcion | 1096 |
| academico.cd_prueba_diagnostica | 143 |
| academico.curso | 50 |
| academico.estudiante | 420 |
| academico.estudiante_requisito | 1680 |
| academico.inscripcion | 9218 |
| academico.matricula | 1708 |
| academico.periodo | 12 |
| academico.prerrequisito | 52 |
| academico.programa | 1 |
| academico.requisito_grado | 4 |
| chatbot.alerta_temprana | 25 |
| chatbot.calendario | 27 |
| chatbot.conversacion_log | 86 |
| chatbot.noticia | 204 |
| chatbot.rag_documentos | 276 |


## Vistas analíticas

`academico.v_alertas`, `academico.v_avance_plan`, `academico.v_competencias_digitales`, `academico.v_cursos_habilitados`, `academico.v_estadistica_curso`, `academico.v_estudiante_resumen`, `academico.v_historial_academico`, `academico.v_indicadores_programa`, `academico.v_pga_periodo`, `academico.v_profundidad_curso`


## Estudiantes (muestra)

```sql
select codigo, nombres, apellidos, cohorte, colegio_tipo, puntaje_saber11, trabaja from academico.estudiante order by codigo limit 5
```

| codigo | nombres | apellidos | cohorte | colegio_tipo | puntaje_saber11 | trabaja |
|---|---|---|---|---|---|---|
| U00100001 | Valentina | Rojas Duarte | 2024-1 | Público | 376 | False |
| U00100002 | Andrés Felipe | Gómez Pinzón | 2025-1 | Público | 245 | True |
| U00100003 | Laura Camila | Martínez Ardila | 2022-1 | Privado | 325 | False |
| U00100004 | Santiago | Herrera Quintero | 2026-2 | Privado | 312 | False |
| U00100005 | María José | Castillo Vera | 2023-2 | Privado | 296 | True |


## Cursos y prerrequisitos (muestra)

```sql
select c.curso_id, c.nombre, c.semestre_sugerido, c.creditos, coalesce(string_agg(pr.nombre, ', '), '—') prerrequisitos from academico.curso c left join academico.prerrequisito p on p.curso_id=c.curso_id left join academico.curso pr on pr.curso_id=p.requisito_id where c.semestre_sugerido between 2 and 4 group by 1,2,3,4 order by c.semestre_sugerido, c.curso_id limit 8
```

| curso_id | nombre | semestre_sugerido | creditos | prerrequisitos |
|---|---|---|---|---|
| ISIS1201 | Cálculo Integral | 2 | 4 | Cálculo Diferencial |
| ISIS1202 | Física Mecánica | 2 | 4 | Cálculo Diferencial |
| ISIS1203 | Programación Orientada a Objetos | 2 | 4 | Fundamentos de Programación |
| ISIS1204 | Matemáticas Discretas | 2 | 3 | Álgebra Lineal |
| ISIS1205 | Inglés II | 2 | 2 | Inglés I |
| ISIS1206 | Ética y Ciudadanía | 2 | 2 | — |
| ISIS2301 | Cálculo Multivariable | 3 | 3 | Cálculo Integral |
| ISIS2302 | Ecuaciones Diferenciales | 3 | 3 | Álgebra Lineal, Cálculo Integral |


## Notas de un estudiante (U00100002)

```sql
select i.periodo_id, c.nombre curso, i.nota_final, i.estado from academico.inscripcion i join academico.curso c on c.curso_id=i.curso_id where i.codigo='U00100002' order by i.periodo_id, c.nombre limit 10
```

| periodo_id | curso | nota_final | estado |
|---|---|---|---|
| 2025-1 | Álgebra Lineal | 2.7 | Reprobado |
| 2025-1 | Cálculo Diferencial | 2.4 | Reprobado |
| 2025-1 | Cátedra UNAB y Proyecto de Vida | 3.4 | Aprobado |
| 2025-1 | Fundamentos de Programación | 2.9 | Reprobado |
| 2025-1 | Introducción a la Ingeniería de Sistemas | None | Cancelado |
| 2025-2 | Álgebra Lineal | None | Cancelado |
| 2025-2 | Cálculo Diferencial | 1.9 | Reprobado |
| 2025-2 | Fundamentos de Programación | 4.2 | Aprobado |
| 2026-1 | Álgebra Lineal | 3.0 | Aprobado |
| 2026-1 | Cálculo Diferencial | 2.5 | Reprobado |


## Vista v_estudiante_resumen (cuentas demo)

```sql
select codigo, pga_acumulado, estado_academico, creditos_aprobados, porcentaje_avance, estado_matricula_actual from academico.v_estudiante_resumen where codigo between 'U00100001' and 'U00100005' order by codigo
```

| codigo | pga_acumulado | estado_academico | creditos_aprobados | porcentaje_avance | estado_matricula_actual |
|---|---|---|---|---|---|
| U00100001 | 4.14 | Normal | 87 | 56.5 | Matriculado |
| U00100002 | 2.95 | En prueba académica | 14 | 9.1 | Matriculado |
| U00100003 | 3.78 | Normal | 142 | 92.2 | Matriculado |
| U00100004 | None | Sin calificaciones | 0 | 0.0 | Matriculado |
| U00100005 | 3.20 | Normal | 56 | 36.4 | Pendiente de pago |


## Vista v_alertas (U00100002)

```sql
select tipo, prioridad, left(mensaje,90) mensaje from academico.v_alertas where codigo='U00100002'
```

| tipo | prioridad | mensaje |
|---|---|---|
| Estado académico | ALTA | Estás en prueba académica (PGA del periodo 2026-1: 3.09). Según el art. 24 del Reglamento, |
| Competencias digitales | MEDIA | No has completado la Ruta 3 (Tecnología Transformativa) del Centro de Competencias Digital |
| Competencias digitales | MEDIA | No has completado la Ruta 1 (Competencias Digitales Básicas) del Centro de Competencias Di |
