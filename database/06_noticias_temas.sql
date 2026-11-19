-- =============================================================================
-- 06 · Noticias multifuente por tema (aditivo e idempotente)
-- El scraper (scraper/scraper_noticias.py) trae, además de unab.edu.co, noticias
-- del día de fuentes RSS públicas sobre educación, tecnología e ingeniería de
-- sistemas. Cada noticia queda clasificada en un tema y con el nombre del medio.
-- =============================================================================

ALTER TABLE chatbot.noticia ADD COLUMN IF NOT EXISTS tema TEXT;
ALTER TABLE chatbot.noticia ADD COLUMN IF NOT EXISTS fuente_nombre TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'ck_noticia_tema' AND conrelid = 'chatbot.noticia'::regclass) THEN
        ALTER TABLE chatbot.noticia ADD CONSTRAINT ck_noticia_tema
            CHECK (tema IS NULL OR tema IN ('educacion', 'tecnologia', 'ingenieria_sistemas', 'institucional'));
    END IF;
END $$;

-- Las noticias existentes provienen todas de unab.edu.co
UPDATE chatbot.noticia SET fuente_nombre = 'UNAB' WHERE fuente_nombre IS NULL;
UPDATE chatbot.noticia SET tema = 'institucional' WHERE tema IS NULL;

CREATE INDEX IF NOT EXISTS ix_noticia_tema_fecha ON chatbot.noticia (tema, fecha_pub DESC);

-- mcp_readonly ya tiene SELECT sobre todas las tablas de chatbot (03_functions_security.sql);
-- se repite por si la tabla se recreó después.
GRANT SELECT ON chatbot.noticia TO mcp_readonly;
