-- =====================================================================
--  02_views.sql — Vistas analíticas optimizadas para agentes conversacionales
--  Cada vista devuelve filas "listas para narrar": nombres legibles, totales
--  ya calculados y textos de alerta, para que el LLM no tenga que hacer
--  aritmética (reduce alucinaciones).
-- =====================================================================

-- ---------------------------------------------------------------------
-- PGA por periodo y estado académico (Reglamento 2019, art. 24)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_pga_periodo AS
WITH base AS (
    SELECT i.codigo, i.periodo_id, p.anio, p.numero,
           SUM(i.nota_final * c.creditos) / NULLIF(SUM(c.creditos), 0) AS pga_periodo,
           SUM(c.creditos) FILTER (WHERE i.estado = 'Aprobado')        AS creditos_aprobados,
           SUM(c.creditos)                                              AS creditos_evaluados,
           COUNT(*) FILTER (WHERE i.estado = 'Reprobado')               AS cursos_reprobados
    FROM academico.inscripcion i
    JOIN academico.curso   c USING (curso_id)
    JOIN academico.periodo p USING (periodo_id)
    WHERE i.nota_final IS NOT NULL
    GROUP BY i.codigo, i.periodo_id, p.anio, p.numero
), clasif AS (
    SELECT b.*,
           CASE WHEN pga_periodo > 3.20 THEN 'N'
                WHEN pga_periodo >= 3.00 THEN 'C'
                ELSE 'P' END AS banda,
           LAG(CASE WHEN pga_periodo > 3.20 THEN 'N' WHEN pga_periodo >= 3.00 THEN 'C' ELSE 'P' END)
             OVER (PARTITION BY codigo ORDER BY anio, numero) AS banda_prev
    FROM base b
)
SELECT codigo, periodo_id, anio, numero,
       ROUND(pga_periodo, 2) AS pga_periodo,
       creditos_aprobados, creditos_evaluados, cursos_reprobados,
       CASE WHEN banda = 'N' THEN 'Normal'
            WHEN banda = 'P' THEN 'En prueba académica'
            WHEN banda = 'C' AND banda_prev IN ('C','P') THEN 'En prueba académica'
            ELSE 'Condicional' END AS estado_academico
FROM clasif;

-- ---------------------------------------------------------------------
-- Resumen 360° del estudiante (la vista más usada por el chatbot)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_estudiante_resumen AS
WITH aprob AS (
    -- cada curso cuenta una sola vez aunque tenga más de un registro aprobado/homologado
    SELECT d.codigo, SUM(d.creditos) AS creditos_aprobados, COUNT(*) AS cursos_aprobados
    FROM (SELECT DISTINCT i.codigo, i.curso_id, c.creditos
          FROM academico.inscripcion i JOIN academico.curso c USING (curso_id)
          WHERE i.estado IN ('Aprobado','Homologado')) d
    GROUP BY d.codigo
), acum AS (
    SELECT i.codigo,
           ROUND(SUM(i.nota_final * c.creditos) / NULLIF(SUM(c.creditos),0), 2) AS pga_acumulado,
           COUNT(*) FILTER (WHERE i.estado = 'Reprobado') AS total_reprobados
    FROM academico.inscripcion i JOIN academico.curso c USING (curso_id)
    WHERE i.nota_final IS NOT NULL
    GROUP BY i.codigo
), ultimo AS (
    SELECT DISTINCT ON (codigo) codigo, periodo_id AS ultimo_periodo_evaluado, pga_periodo, estado_academico
    FROM academico.v_pga_periodo
    ORDER BY codigo, anio DESC, numero DESC
), cursando AS (
    SELECT i.codigo, COUNT(*) AS cursos_en_curso, SUM(c.creditos) AS creditos_en_curso
    FROM academico.inscripcion i JOIN academico.curso c USING (curso_id)
    WHERE i.estado = 'Cursando'
    GROUP BY i.codigo
), periodos AS (
    SELECT codigo, COUNT(*) FILTER (WHERE estado = 'Matriculado') AS periodos_cursados
    FROM academico.matricula GROUP BY codigo
)
SELECT e.codigo,
       e.nombres || ' ' || e.apellidos                         AS nombre_completo,
       e.email, e.programa_id, pr.nombre                        AS programa,
       e.cohorte, e.condicion, e.trabaja, e.beca,
       COALESCE(pe.periodos_cursados, 0)                        AS periodos_cursados,
       -- semestre según créditos aprobados (criterio Registro Académico)
       LEAST(9, 1 + FLOOR(COALESCE(a.creditos_aprobados,0) / (pr.creditos_totales / 9.0)))::int AS semestre_por_creditos,
       COALESCE(a.creditos_aprobados, 0)                        AS creditos_aprobados,
       pr.creditos_totales,
       pr.creditos_totales - COALESCE(a.creditos_aprobados, 0)  AS creditos_pendientes,
       ROUND(100.0 * COALESCE(a.creditos_aprobados,0) / pr.creditos_totales, 1) AS porcentaje_avance,
       COALESCE(a.cursos_aprobados, 0)                          AS cursos_aprobados,
       COALESCE(ac.total_reprobados, 0)                         AS total_reprobados,
       ac.pga_acumulado,
       u.ultimo_periodo_evaluado, u.pga_periodo                 AS pga_ultimo_periodo,
       COALESCE(u.estado_academico, 'Sin calificaciones')      AS estado_academico,
       COALESCE(cu.cursos_en_curso, 0)                          AS cursos_en_curso,
       COALESCE(cu.creditos_en_curso, 0)                        AS creditos_en_curso,
       m.estado                                                 AS estado_matricula_actual,
       m.valor_liquidado - m.valor_pagado                       AS saldo_pendiente
FROM academico.estudiante e
JOIN academico.programa pr USING (programa_id)
LEFT JOIN aprob    a  USING (codigo)
LEFT JOIN acum     ac USING (codigo)
LEFT JOIN ultimo   u  USING (codigo)
LEFT JOIN cursando cu USING (codigo)
LEFT JOIN periodos pe USING (codigo)
LEFT JOIN academico.matricula m
       ON m.codigo = e.codigo
      AND m.periodo_id = (SELECT periodo_id FROM academico.periodo WHERE es_actual);

-- ---------------------------------------------------------------------
-- Historial académico legible
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_historial_academico AS
SELECT i.codigo, i.periodo_id, c.semestre_sugerido, i.curso_id, c.nombre AS curso,
       c.creditos, i.nota_final, i.estado,
       ROW_NUMBER() OVER (PARTITION BY i.codigo, i.curso_id ORDER BY i.periodo_id) AS intento
FROM academico.inscripcion i
JOIN academico.curso c USING (curso_id);

-- ---------------------------------------------------------------------
-- Avance del plan: cada curso del plan con su estado para el estudiante
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_avance_plan AS
SELECT e.codigo, c.semestre_sugerido, c.curso_id, c.nombre AS curso, c.creditos, c.componente,
       CASE
         WHEN bool_or(i.estado IN ('Aprobado','Homologado')) THEN 'Aprobado'
         WHEN bool_or(i.estado = 'Cursando')                 THEN 'Cursando'
         WHEN bool_or(i.estado = 'Reprobado')                THEN 'Reprobado (pendiente)'
         ELSE 'Pendiente'
       END AS estado,
       MAX(i.nota_final) FILTER (WHERE i.estado IN ('Aprobado','Homologado')) AS nota_aprobacion,
       COUNT(i.*) FILTER (WHERE i.estado = 'Reprobado') AS veces_reprobado
FROM academico.estudiante e
CROSS JOIN academico.curso c
LEFT JOIN academico.inscripcion i ON i.codigo = e.codigo AND i.curso_id = c.curso_id
WHERE c.programa_id = e.programa_id
GROUP BY e.codigo, c.semestre_sugerido, c.curso_id, c.nombre, c.creditos, c.componente;

-- ---------------------------------------------------------------------
-- Cursos habilitados: pendientes cuyo prerrequisito ya está aprobado
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_cursos_habilitados AS
SELECT ap.codigo, ap.curso_id, ap.curso, ap.creditos, ap.semestre_sugerido, ap.estado,
       (ap.estado = 'Reprobado (pendiente)') AS es_repitencia
FROM academico.v_avance_plan ap
JOIN academico.v_estudiante_resumen r USING (codigo)
WHERE ap.estado IN ('Pendiente','Reprobado (pendiente)')
  AND NOT EXISTS (                      -- todos los cursos prerrequisito aprobados
        SELECT 1 FROM academico.prerrequisito p
        WHERE p.curso_id = ap.curso_id AND p.tipo = 'prerrequisito'
          AND NOT EXISTS (SELECT 1 FROM academico.inscripcion i
                          WHERE i.codigo = ap.codigo AND i.curso_id = p.requisito_id
                            AND i.estado IN ('Aprobado','Homologado')))
  AND NOT EXISTS (                      -- créditos mínimos cumplidos
        SELECT 1 FROM academico.prerrequisito p
        WHERE p.curso_id = ap.curso_id AND p.tipo = 'creditos'
          AND p.creditos_min > r.creditos_aprobados);

-- ---------------------------------------------------------------------
-- Cadena crítica de prerrequisitos (semestres mínimos para terminar)
-- Longest path del DAG de prerrequisitos restringido a cursos no aprobados
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_profundidad_curso AS
WITH RECURSIVE cadena AS (
    SELECT c.curso_id, c.curso_id AS raiz, 1 AS nivel
    FROM academico.curso c
    UNION ALL
    SELECT p.curso_id, ch.raiz, ch.nivel + 1
    FROM cadena ch
    JOIN academico.prerrequisito p ON p.requisito_id = ch.curso_id AND p.tipo = 'prerrequisito'
)
SELECT raiz AS curso_id, MAX(nivel) AS cursos_que_dependen_en_cadena,
       COUNT(DISTINCT curso_id) - 1 AS cursos_bloqueados
FROM cadena GROUP BY raiz;

-- ---------------------------------------------------------------------
-- Competencias digitales por ruta (incluye homologación de oferta antigua)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_competencias_digitales AS
WITH ok AS (
    SELECT ci.codigo,
           COALESCE(NULLIF(cc.ruta,0), eq.ruta) AS ruta,
           COALESCE(eq.nombre, cc.nombre)       AS curso_reconocido,
           cc.nombre                            AS curso_tomado,
           ci.estado, ci.periodo_id
    FROM academico.cd_inscripcion ci
    JOIN academico.cd_curso cc USING (cd_curso_id)
    LEFT JOIN academico.cd_curso eq ON eq.cd_curso_id = cc.equivale_a
    WHERE ci.estado IN ('Aprobado','Validado por prueba','Cursando')
), rutas AS (
    SELECT DISTINCT ruta, ruta_nombre FROM academico.cd_curso WHERE ruta > 0
)
SELECT e.codigo, r.ruta, r.ruta_nombre,
       COALESCE(bool_or(ok.estado IN ('Aprobado','Validado por prueba')), FALSE) AS cumplida,
       COALESCE(bool_or(ok.estado = 'Cursando'), FALSE)                         AS en_curso,
       string_agg(DISTINCT ok.curso_tomado || ' (' || ok.estado || ', ' || ok.periodo_id || ')', '; ') AS detalle
FROM academico.estudiante e
CROSS JOIN rutas r
LEFT JOIN ok ON ok.codigo = e.codigo AND ok.ruta = r.ruta
GROUP BY e.codigo, r.ruta, r.ruta_nombre;

-- ---------------------------------------------------------------------
-- Estadística por curso (para recomendaciones basadas en datos)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_estadistica_curso AS
SELECT c.curso_id, c.nombre AS curso, c.semestre_sugerido, c.creditos,
       COUNT(i.*) FILTER (WHERE i.nota_final IS NOT NULL)                   AS intentos,
       ROUND(AVG(i.nota_final), 2)                                          AS nota_promedio,
       ROUND(100.0 * COUNT(*) FILTER (WHERE i.estado = 'Reprobado')
             / NULLIF(COUNT(*) FILTER (WHERE i.nota_final IS NOT NULL),0), 1) AS tasa_reprobacion,
       COALESCE(pc.cursos_bloqueados, 0)                                    AS cursos_que_bloquea
FROM academico.curso c
LEFT JOIN academico.inscripcion i USING (curso_id)
LEFT JOIN academico.v_profundidad_curso pc USING (curso_id)
GROUP BY c.curso_id, c.nombre, c.semestre_sugerido, c.creditos, pc.cursos_bloqueados;

-- ---------------------------------------------------------------------
-- Alertas de requisitos pendientes (texto listo para el chatbot)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_alertas AS
-- 1. Estado académico de riesgo
SELECT r.codigo, 'ALTA' AS prioridad, 'Estado académico' AS tipo,
       'Estás ' || lower(r.estado_academico) || ' (PGA del periodo ' || r.ultimo_periodo_evaluado || ': '
       || r.pga_ultimo_periodo || '). Según el art. 24 del Reglamento, debes superar 3.20 para volver a estado Normal.' AS mensaje
FROM academico.v_estudiante_resumen r
WHERE r.estado_academico IN ('Condicional','En prueba académica')
UNION ALL
-- 2. Matrícula pendiente
SELECT r.codigo, 'ALTA', 'Matrícula',
       'Tu matrícula del periodo actual está en estado "' || r.estado_matricula_actual || '"'
       || CASE WHEN r.saldo_pendiente > 0 THEN ' con saldo pendiente de $' || to_char(r.saldo_pendiente, 'FM999G999G999') ELSE '' END
       || '. Formalízala para no perder tus cursos.'
FROM academico.v_estudiante_resumen r
WHERE r.estado_matricula_actual IN ('Pendiente de pago','Pre-matriculado','No matriculado')
  AND r.condicion = 'Activo'
UNION ALL
-- 3. Cursos reprobados que bloquean otros
SELECT ap.codigo, CASE WHEN ap.veces_reprobado >= 2 THEN 'ALTA' ELSE 'MEDIA' END, 'Cuello de botella',
       'Tienes pendiente ' || ap.curso || ' (reprobado ' || ap.veces_reprobado || ' vez/veces) y es prerrequisito en cadena de '
       || pc.cursos_bloqueados || ' cursos. Priorízalo en tu próxima matrícula.'
FROM academico.v_avance_plan ap
JOIN academico.v_profundidad_curso pc USING (curso_id)
WHERE ap.estado = 'Reprobado (pendiente)' AND pc.cursos_bloqueados >= 2
UNION ALL
-- 4. Rutas de competencias digitales sin cumplir (recomendadas en los 3 primeros semestres)
SELECT cd.codigo, CASE WHEN r.periodos_cursados >= 3 THEN 'MEDIA' ELSE 'BAJA' END, 'Competencias digitales',
       'No has completado la Ruta ' || cd.ruta || ' (' || cd.ruta_nombre || ') del Centro de Competencias Digitales. '
       || 'Es requisito de grado y se recomienda terminarla en los tres primeros semestres.'
FROM academico.v_competencias_digitales cd
JOIN academico.v_estudiante_resumen r USING (codigo)
WHERE NOT cd.cumplida AND NOT cd.en_curso
UNION ALL
-- 5. Requisitos de grado cuando se acerca la práctica (>= 100 créditos)
SELECT er.codigo, 'MEDIA', 'Requisito de grado',
       'Requisito de grado pendiente: ' || rg.nombre || ' — ' || rg.descripcion
FROM academico.estudiante_requisito er
JOIN academico.requisito_grado rg USING (requisito_id)
JOIN academico.v_estudiante_resumen r USING (codigo)
WHERE NOT er.cumplido AND er.requisito_id <> 'CD_RUTAS' AND r.creditos_aprobados >= 100
UNION ALL
-- 6. Habilitado para práctica profesional
SELECT r.codigo, 'INFO', 'Práctica profesional',
       'Ya cumples los 130 créditos aprobados exigidos para inscribir la Práctica Profesional.'
FROM academico.v_estudiante_resumen r
WHERE r.creditos_aprobados >= 130
  AND NOT EXISTS (SELECT 1 FROM academico.inscripcion i WHERE i.codigo = r.codigo AND i.curso_id = 'ISIS5901');

-- ---------------------------------------------------------------------
-- Vista agregada para el tablero de la app y la analítica del programa
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW academico.v_indicadores_programa AS
SELECT COUNT(*) FILTER (WHERE condicion = 'Activo')                         AS estudiantes_activos,
       ROUND(AVG(pga_acumulado) FILTER (WHERE condicion = 'Activo'), 2)       AS pga_promedio_activos,
       COUNT(*) FILTER (WHERE estado_academico = 'En prueba académica' AND condicion = 'Activo') AS en_prueba_academica,
       COUNT(*) FILTER (WHERE estado_academico = 'Condicional' AND condicion = 'Activo')          AS condicionales,
       COUNT(*) FILTER (WHERE condicion IN ('Desertor','Retirado','Inactivo'))                    AS no_activos,
       ROUND(100.0 * COUNT(*) FILTER (WHERE condicion IN ('Desertor','Retirado','Inactivo')) / COUNT(*), 1) AS tasa_desercion
FROM academico.v_estudiante_resumen;
