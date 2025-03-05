-- 003_add_base_id_to_knowledge.sql
BEGIN;

-- Añadir la columna base_id a la tabla knowledge si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge' AND column_name = 'base_id'
    ) THEN
        ALTER TABLE knowledge ADD COLUMN base_id INTEGER;
        
        -- Opcional: Añadir una clave foránea si base_id hace referencia a otra tabla
        -- ALTER TABLE knowledge ADD CONSTRAINT knowledge_base_id_fkey 
        -- FOREIGN KEY (base_id) REFERENCES knowledge_bases(id);
    END IF;
END $$;

-- Añadir columna content_hash si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'knowledge' AND column_name = 'content_hash'
    ) THEN
        ALTER TABLE knowledge ADD COLUMN content_hash VARCHAR(255);
    END IF;
END $$;

-- Registrar la migración
INSERT INTO migration_history (file_name) VALUES ('003_add_base_id_to_knowledge.sql')
ON CONFLICT (file_name) DO NOTHING;

COMMIT;