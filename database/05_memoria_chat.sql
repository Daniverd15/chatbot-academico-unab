-- =====================================================================
--  05_memoria_chat.sql — Memoria conversacional limpia (aditivo e idempotente)
--  Los agentes de n8n guardan en n8n_chat_histories también los pasos
--  intermedios de herramientas (mensajes "ai" con tool_calls y mensajes
--  "tool"). La memoria de ventana (últimos N mensajes) puede cortar justo
--  en medio de una llamada a herramienta y Gemini rechaza el historial:
--  "function call turn comes immediately after a user turn ...".
--  Solución: conservar solo los turnos de texto humano/asistente. Los datos
--  que devolvieron las herramientas ya están resumidos en la respuesta.
-- =====================================================================

CREATE OR REPLACE FUNCTION public.n8n_memoria_solo_texto() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.message->>'type' = 'tool'
       OR (NEW.message->>'type' = 'ai'
           AND jsonb_typeof(NEW.message->'tool_calls') = 'array'
           AND jsonb_array_length(NEW.message->'tool_calls') > 0) THEN
        RETURN NULL;  -- descarta el paso intermedio
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_memoria_solo_texto ON public.n8n_chat_histories;
CREATE TRIGGER trg_memoria_solo_texto
    BEFORE INSERT ON public.n8n_chat_histories
    FOR EACH ROW EXECUTE FUNCTION public.n8n_memoria_solo_texto();

-- Limpia el historial existente
DELETE FROM public.n8n_chat_histories
WHERE message->>'type' = 'tool'
   OR (message->>'type' = 'ai'
       AND jsonb_typeof(message->'tool_calls') = 'array'
       AND jsonb_array_length(message->'tool_calls') > 0);
