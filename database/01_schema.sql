-- =====================================================================
--  Chatbot de Apoyo Académico UNAB · Ingeniería de Sistemas
--  01_schema.sql — Modelo relacional que simula Banner / COSMOS
--  Motor: PostgreSQL 15+ (Supabase) con extensión pgvector
-- =====================================================================
--  Convenciones
--   * Esquema `academico`  : datos transaccionales tipo Banner/COSMOS
--   * Esquema `chatbot`    : RAG, noticias, calendario, logs del bot
--   * Las notas siguen la escala UNAB 0.0 – 5.0 (aprobatoria >= 3.0)
--   * Estados académicos según Reglamento Estudiantil de Pregrado 2019,
--     art. 24 (Normal > 3.20, Condicional 3.00–3.20, Prueba < 3.00 ...)
-- =====================================================================

-- En Supabase las extensiones viven en el esquema `extensions`
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector   WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
SET search_path = public, extensions;

DROP SCHEMA IF EXISTS academico CASCADE;
DROP SCHEMA IF EXISTS chatbot   CASCADE;
CREATE SCHEMA academico;
CREATE SCHEMA chatbot;

-- ---------------------------------------------------------------------
--  CATÁLOGOS
-- ---------------------------------------------------------------------
CREATE TABLE academico.programa (
    programa_id        TEXT PRIMARY KEY,                 -- 'ISIS'
    nombre             TEXT NOT NULL,
    facultad           TEXT NOT NULL,
    snies              TEXT,
    modalidad          TEXT NOT NULL DEFAULT 'Presencial',
    semestres          SMALLINT NOT NULL,
    creditos_totales   SMALLINT NOT NULL,
    max_creditos_sem   SMALLINT NOT NULL DEFAULT 20,
    titulo_otorgado    TEXT
);

CREATE TABLE academico.periodo (
    periodo_id     TEXT PRIMARY KEY,                     -- '2026-2'
    anio           SMALLINT NOT NULL,
    numero         SMALLINT NOT NULL CHECK (numero IN (1, 2)),
    fecha_inicio   DATE NOT NULL,
    fecha_fin      DATE NOT NULL,
    es_actual      BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX ux_periodo_actual ON academico.periodo (es_actual) WHERE es_actual;

CREATE TABLE academico.curso (
    curso_id           TEXT PRIMARY KEY,                 -- 'ISIS1101'
    programa_id        TEXT NOT NULL REFERENCES academico.programa,
    nombre             TEXT NOT NULL,
    creditos           SMALLINT NOT NULL CHECK (creditos BETWEEN 0 AND 12),
    semestre_sugerido  SMALLINT NOT NULL,
    componente         TEXT NOT NULL CHECK (componente IN
                       ('Básico','Específico','Flexible','Socio-humanístico','Instrumental','Práctica')),
    area               TEXT NOT NULL,
    tipo               TEXT NOT NULL DEFAULT 'Regular' CHECK (tipo IN ('Regular','Electivo')),
    dificultad         NUMERIC(3,2) NOT NULL DEFAULT 0.50,   -- 0..1, usado por el simulador
    descripcion        TEXT
);

-- Prerrequisitos: un curso puede exigir otros cursos o un mínimo de créditos.
CREATE TABLE academico.prerrequisito (
    curso_id        TEXT NOT NULL REFERENCES academico.curso ON DELETE CASCADE,
    requisito_id    TEXT REFERENCES academico.curso,
    creditos_min    SMALLINT,
    tipo            TEXT NOT NULL DEFAULT 'prerrequisito'
                    CHECK (tipo IN ('prerrequisito','correquisito','creditos')),
    CHECK ((tipo = 'creditos' AND creditos_min IS NOT NULL AND requisito_id IS NULL)
        OR (tipo <> 'creditos' AND requisito_id IS NOT NULL))
);
CREATE UNIQUE INDEX ux_prerreq ON academico.prerrequisito (curso_id, COALESCE(requisito_id,''), tipo);

-- Requisitos de grado distintos a los cursos del plan
CREATE TABLE academico.requisito_grado (
    requisito_id   TEXT PRIMARY KEY,                     -- 'INGLES_B1'
    nombre         TEXT NOT NULL,
    descripcion    TEXT NOT NULL
);

-- ---------------------------------------------------------------------
--  ESTUDIANTES Y MATRÍCULA (simulación Banner / COSMOS)
-- ---------------------------------------------------------------------
CREATE TABLE academico.estudiante (
    codigo            TEXT PRIMARY KEY,                  -- 'U00178823'
    documento         TEXT UNIQUE NOT NULL,
    nombres           TEXT NOT NULL,
    apellidos         TEXT NOT NULL,
    email             TEXT UNIQUE NOT NULL,
    genero            CHAR(1) CHECK (genero IN ('F','M','O')),
    fecha_nacimiento  DATE,
    ciudad_origen     TEXT,
    colegio_tipo      TEXT CHECK (colegio_tipo IN ('Público','Privado')),
    puntaje_saber11   SMALLINT,
    programa_id       TEXT NOT NULL REFERENCES academico.programa,
    cohorte           TEXT NOT NULL REFERENCES academico.periodo,
    condicion         TEXT NOT NULL DEFAULT 'Activo' CHECK (condicion IN
                      ('Activo','En reserva de cupo','En reintegro','Desertor','Inactivo',
                       'Egresado','Graduado','Retirado')),
    trabaja           BOOLEAN NOT NULL DEFAULT FALSE,
    beca              TEXT,                              -- NULL = sin beca
    pin_acceso        TEXT NOT NULL,                     -- hash bcrypt del PIN de la app
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Estado de matrícula financiera/académica por periodo
CREATE TABLE academico.matricula (
    codigo             TEXT NOT NULL REFERENCES academico.estudiante ON DELETE CASCADE,
    periodo_id         TEXT NOT NULL REFERENCES academico.periodo,
    estado             TEXT NOT NULL CHECK (estado IN
                       ('Matriculado','Pre-matriculado','Pendiente de pago','Reserva de cupo','No matriculado')),
    fecha_matricula    DATE,
    valor_liquidado    NUMERIC(12,0),
    valor_pagado       NUMERIC(12,0) NOT NULL DEFAULT 0,
    creditos_inscritos SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (codigo, periodo_id)
);

-- Historial de cursos: una fila por intento
CREATE TABLE academico.inscripcion (
    inscripcion_id   BIGSERIAL PRIMARY KEY,
    codigo           TEXT NOT NULL REFERENCES academico.estudiante ON DELETE CASCADE,
    curso_id         TEXT NOT NULL REFERENCES academico.curso,
    periodo_id       TEXT NOT NULL REFERENCES academico.periodo,
    nota_final       NUMERIC(2,1) CHECK (nota_final BETWEEN 0 AND 5),
    estado           TEXT NOT NULL CHECK (estado IN ('Aprobado','Reprobado','Cursando','Cancelado','Homologado')),
    UNIQUE (codigo, curso_id, periodo_id)
);
CREATE INDEX ix_inscripcion_codigo ON academico.inscripcion (codigo);
CREATE INDEX ix_inscripcion_curso  ON academico.inscripcion (curso_id);

CREATE TABLE academico.estudiante_requisito (
    codigo          TEXT NOT NULL REFERENCES academico.estudiante ON DELETE CASCADE,
    requisito_id    TEXT NOT NULL REFERENCES academico.requisito_grado,
    cumplido        BOOLEAN NOT NULL DEFAULT FALSE,
    fecha           DATE,
    detalle         TEXT,
    PRIMARY KEY (codigo, requisito_id)
);

-- ---------------------------------------------------------------------
--  COMPETENCIAS DIGITALES (Centro de Competencias Digitales — CCD)
--  Ruta 1: Competencias Digitales Básicas (obligatoria)
--  Ruta 2: Analítica y Contenido Digital (elegir 1)
--  Ruta 3: Tecnología Transformativa     (elegir 1)
-- ---------------------------------------------------------------------
CREATE TABLE academico.cd_curso (
    cd_curso_id    TEXT PRIMARY KEY,                     -- 'CD-R1-ID'
    nombre         TEXT NOT NULL,
    ruta           SMALLINT NOT NULL CHECK (ruta IN (0,1,2,3)),   -- 0 = oferta anterior a 2026
    ruta_nombre    TEXT NOT NULL,
    horas          SMALLINT NOT NULL,
    modalidad      TEXT NOT NULL,
    vigente        BOOLEAN NOT NULL DEFAULT TRUE,
    equivale_a     TEXT REFERENCES academico.cd_curso,  -- homologación oferta antigua → nueva
    descripcion    TEXT
);

CREATE TABLE academico.cd_inscripcion (
    cd_inscripcion_id BIGSERIAL PRIMARY KEY,
    codigo         TEXT NOT NULL REFERENCES academico.estudiante ON DELETE CASCADE,
    cd_curso_id    TEXT NOT NULL REFERENCES academico.cd_curso,
    periodo_id     TEXT NOT NULL REFERENCES academico.periodo,
    ciclo          TEXT,                                 -- 'Mensual 3', 'Vacacional'
    estado         TEXT NOT NULL CHECK (estado IN ('Aprobado','Reprobado','Inscrito','Cursando','Validado por prueba')),
    nota           NUMERIC(2,1),
    fecha          DATE
);
CREATE INDEX ix_cd_inscripcion_codigo ON academico.cd_inscripcion (codigo);

CREATE TABLE academico.cd_prueba_diagnostica (
    codigo         TEXT PRIMARY KEY REFERENCES academico.estudiante ON DELETE CASCADE,
    fecha          DATE NOT NULL,
    puntaje        NUMERIC(5,2) NOT NULL CHECK (puntaje BETWEEN 0 AND 100),
    valida_curso   BOOLEAN GENERATED ALWAYS AS (puntaje >= 70) STORED
);

-- ---------------------------------------------------------------------
--  ESQUEMA CHATBOT
-- ---------------------------------------------------------------------
-- Calendario (copia espejo de Google Sheets para fallback / analítica)
CREATE TABLE chatbot.calendario (
    evento_id    SERIAL PRIMARY KEY,
    periodo_id   TEXT,
    categoria    TEXT NOT NULL,          -- Inscripciones, Prueba diagnóstica, Inicio de cursos ...
    evento       TEXT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin    DATE,
    publico      TEXT,
    fuente       TEXT
);

-- Noticias obtenidas por el scraper periódico
CREATE TABLE chatbot.noticia (
    noticia_id     BIGINT PRIMARY KEY,   -- id del post en el CMS de unab.edu.co
    titulo         TEXT NOT NULL,
    url            TEXT UNIQUE NOT NULL,
    fecha_pub      TIMESTAMPTZ NOT NULL,
    categoria      TEXT,
    tipo           TEXT,                 -- curso, convocatoria, certificación, evento, general
    resumen        TEXT,
    contenido      TEXT,
    relevancia     NUMERIC(4,2),         -- score para estudiantes de sistemas/CD
    scrapeado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_noticia_fecha ON chatbot.noticia (fecha_pub DESC);

-- Base vectorial del RAG (compatible con nodo "Postgres PGVector Store" de n8n)
-- gemini-embedding-001 → 3072 dimensiones
CREATE TABLE chatbot.rag_documentos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text       TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding  vector(3072)
);
-- HNSW sobre halfvec (pgvector >= 0.7): permite indexar 3072 dims (límite vector = 2000)
CREATE INDEX ix_rag_embedding ON chatbot.rag_documentos
    USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);
CREATE INDEX ix_rag_metadata ON chatbot.rag_documentos USING gin (metadata);

-- Bitácora de conversaciones (analítica + auditoría de guardrails)
CREATE TABLE chatbot.conversacion_log (
    log_id          BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    codigo          TEXT,
    canal           TEXT NOT NULL DEFAULT 'app',
    intencion       TEXT,
    pregunta        TEXT NOT NULL,
    respuesta       TEXT,
    guardrail_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    bloqueado       BOOLEAN NOT NULL DEFAULT FALSE,
    latencia_ms     INTEGER,
    calificacion    SMALLINT CHECK (calificacion BETWEEN 1 AND 5),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_log_session ON chatbot.conversacion_log (session_id, creado_en);

-- Memoria persistente del agente (misma estructura que crea n8n "Postgres Chat Memory")
CREATE TABLE IF NOT EXISTS public.n8n_chat_histories (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(255) NOT NULL,
    message     JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chat_hist_session ON public.n8n_chat_histories (session_id);
