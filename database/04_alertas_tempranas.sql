-- =====================================================================
--  04_alertas_tempranas.sql — Alertas tempranas proactivas (aditivo e idempotente)
--  Mensajes de acompañamiento generados por el workflow 08 de n8n para que
--  consejería los revise antes de contactar al estudiante.
--  Requiere 01_schema.sql y 03_functions_security.sql (rol mcp_readonly).
-- =====================================================================

CREATE TABLE IF NOT EXISTS chatbot.alerta_temprana (
    id           BIGSERIAL PRIMARY KEY,
    codigo       TEXT        NOT NULL,
    generada_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- date(timestamptz) no es inmutable: se guarda el día aparte para la unicidad
    fecha        DATE        NOT NULL DEFAULT current_date,
    nivel        TEXT        NOT NULL,
    motivos      JSONB       NOT NULL DEFAULT '[]'::jsonb,
    mensaje      TEXT        NOT NULL,
    estado       TEXT        NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente', 'revisada', 'enviada')),
    UNIQUE (codigo, fecha)
);

CREATE INDEX IF NOT EXISTS idx_alerta_temprana_estado ON chatbot.alerta_temprana (estado, generada_en DESC);

-- Solo lectura para el servidor MCP / observatorio; la escritura la hace n8n (rol dueño)
GRANT SELECT ON chatbot.alerta_temprana TO mcp_readonly;
