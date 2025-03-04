-- 006_agent_multiple_knowledge.sql
BEGIN;

-- Crear tabla para relaciones muchos a muchos entre agentes y documentos
CREATE TABLE IF NOT EXISTS agent_knowledge_items (
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (agent_id, knowledge_id)
);

-- Crear índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_items_agent_id ON agent_knowledge_items(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_items_knowledge_id ON agent_knowledge_items(knowledge_id);

-- Mensaje informativo
DO $$ 
BEGIN
    RAISE NOTICE 'Tabla agent_knowledge_items creada con éxito';
END $$;

COMMIT;