BEGIN;

-- Hacer knowledge_id nullable en la tabla agents
ALTER TABLE agents ALTER COLUMN knowledge_id DROP NOT NULL;

-- Migrar datos existentes a la tabla agent_knowledge_items
INSERT INTO agent_knowledge_items (agent_id, knowledge_id)
SELECT id, knowledge_id FROM agents
WHERE knowledge_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM agent_knowledge_items
    WHERE agent_knowledge_items.agent_id = agents.id
    AND agent_knowledge_items.knowledge_id = agents.knowledge_id
);
DO $$ 
BEGIN
    RAISE NOTICE 'Ejecutado con exito';
END $$;

COMMIT;
