-- =====================================================================
--  03_functions_security.sql — Funciones de búsqueda RAG, autenticación
--  y rol de solo lectura para el servidor MCP (principio de mínimo privilegio)
-- =====================================================================

-- Búsqueda semántica (coseno) con filtro opcional por metadatos
CREATE OR REPLACE FUNCTION chatbot.match_documentos(
    query_embedding vector(3072),
    match_count     INT   DEFAULT 5,
    filtro          JSONB DEFAULT '{}'::jsonb,
    umbral          FLOAT DEFAULT 0.0
) RETURNS TABLE (id UUID, text TEXT, metadata JSONB, similitud FLOAT)
LANGUAGE sql STABLE SET search_path = chatbot, public, extensions AS $$
    SELECT d.id, d.text, d.metadata,
           1 - ((d.embedding::halfvec(3072)) <=> (query_embedding::halfvec(3072))) AS similitud
    FROM chatbot.rag_documentos d
    WHERE d.metadata @> filtro
      AND 1 - ((d.embedding::halfvec(3072)) <=> (query_embedding::halfvec(3072))) >= umbral
    ORDER BY (d.embedding::halfvec(3072)) <=> (query_embedding::halfvec(3072))
    LIMIT match_count;
$$;

-- Búsqueda léxica complementaria (híbrida) en español
CREATE INDEX IF NOT EXISTS ix_rag_fts ON chatbot.rag_documentos
    USING gin (to_tsvector('spanish', text));

CREATE OR REPLACE FUNCTION chatbot.buscar_texto(consulta TEXT, match_count INT DEFAULT 5)
RETURNS TABLE (id UUID, text TEXT, metadata JSONB, rank REAL)
LANGUAGE sql STABLE SET search_path = chatbot, public, extensions AS $$
    SELECT d.id, d.text, d.metadata,
           ts_rank(to_tsvector('spanish', d.text), websearch_to_tsquery('spanish', consulta)) AS rank
    FROM chatbot.rag_documentos d
    WHERE to_tsvector('spanish', d.text) @@ websearch_to_tsquery('spanish', consulta)
    ORDER BY rank DESC
    LIMIT match_count;
$$;

-- Verificación de PIN del estudiante (app móvil). Nunca expone el hash.
CREATE OR REPLACE FUNCTION academico.verificar_pin(p_codigo TEXT, p_pin TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = academico, public, extensions AS $$
    SELECT EXISTS (
        SELECT 1 FROM academico.estudiante
        WHERE codigo = upper(p_codigo)
          AND pin_acceso = encode(digest(upper(p_codigo) || ':' || p_pin, 'sha256'), 'hex')
    );
$$;

-- ---------------------------------------------------------------------
-- Rol de solo lectura para el servidor MCP
-- (la contraseña se asigna desde load_database.py con la variable MCP_DB_PASSWORD)
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_readonly') THEN
        CREATE ROLE mcp_readonly LOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA academico, chatbot, extensions TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA academico TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA chatbot   TO mcp_readonly;
REVOKE SELECT ON academico.estudiante FROM mcp_readonly;          -- oculta pin_acceso / documento
GRANT SELECT (codigo, nombres, apellidos, email, genero, ciudad_origen, colegio_tipo, puntaje_saber11,
              programa_id, cohorte, condicion, trabaja, beca)
      ON academico.estudiante TO mcp_readonly;
GRANT EXECUTE ON FUNCTION chatbot.match_documentos(vector, INT, JSONB, FLOAT) TO mcp_readonly;
GRANT EXECUTE ON FUNCTION chatbot.buscar_texto(TEXT, INT) TO mcp_readonly;
GRANT EXECUTE ON FUNCTION academico.verificar_pin(TEXT, TEXT) TO mcp_readonly;
ALTER ROLE mcp_readonly SET statement_timeout = '8s';
ALTER ROLE mcp_readonly SET search_path = academico, chatbot, public, extensions;

-- Búsqueda insensible a tildes/mayúsculas (usada por info_curso)
CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA extensions;
CREATE OR REPLACE FUNCTION public.unaccent_lower(t TEXT) RETURNS TEXT
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = public, extensions AS $$
    SELECT lower(extensions.unaccent('extensions.unaccent'::regdictionary, t));
$$;
GRANT EXECUTE ON FUNCTION public.unaccent_lower(TEXT) TO mcp_readonly;

-- Vista actualizable en `public` para el nodo "Postgres PGVector Store" de n8n
-- (el nodo espera una tabla sin esquema; inserta y consulta a través de esta vista)
CREATE OR REPLACE VIEW public.rag_documentos AS
    SELECT id, text, metadata, embedding FROM chatbot.rag_documentos;
