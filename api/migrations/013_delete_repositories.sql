-- 003_eliminar_repositories.sql
BEGIN;

-- Primero eliminar el índice que hace referencia a repository_id
DROP INDEX IF EXISTS idx_knowledge_repository_id;

-- Eliminar la restricción de clave foránea que apunta a repositories (si existe)
ALTER TABLE knowledge DROP CONSTRAINT IF EXISTS knowledge_repository_id_fkey;

-- Eliminar la columna repository_id de la tabla knowledge
ALTER TABLE knowledge DROP COLUMN IF EXISTS repository_id;

-- Eliminar la tabla repositories
DROP TABLE IF EXISTS repositories CASCADE;

-- Eliminar referencias en otras tablas si existen
ALTER TABLE analysis_results DROP COLUMN IF EXISTS repo_ids;

-- Registrar la migración
INSERT INTO migration_history (file_name) 
VALUES ('003_eliminar_repositories.sql')
ON CONFLICT (file_name) DO NOTHING;

COMMIT;