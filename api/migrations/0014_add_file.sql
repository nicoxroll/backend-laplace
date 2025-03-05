BEGIN;

-- No necesitas añadir nuevos campos, aprovecha vector_ids que ya existe
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS file_name VARCHAR(255);
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS file_size INTEGER;
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS file_type VARCHAR(100);
ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS job_id VARCHAR(255);

-- Crear índice para búsquedas por job_id
CREATE INDEX IF NOT EXISTS idx_knowledge_job_id ON knowledge(job_id);

COMMIT;