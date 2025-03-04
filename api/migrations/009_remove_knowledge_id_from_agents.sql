BEGIN;

-- Eliminar el índice y la restricción de clave externa
DROP INDEX IF EXISTS uq_user_agent_knowledge;
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_knowledge_id_fkey;

-- Eliminar la columna knowledge_id
ALTER TABLE agents DROP COLUMN IF EXISTS knowledge_id;

-- Mensaje informativo
DO $$ 
BEGIN
    RAISE NOTICE 'Columna knowledge_id eliminada de la tabla agents';
END $$;

COMMIT;