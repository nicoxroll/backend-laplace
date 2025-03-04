BEGIN;

-- Verificar si la columna vector_ids existe y crearla si no
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='knowledge' AND column_name='vector_ids'
    ) THEN
        ALTER TABLE knowledge ADD COLUMN vector_ids JSONB;
        RAISE NOTICE 'Columna vector_ids añadida a la tabla knowledge';
    ELSE
        RAISE NOTICE 'Columna vector_ids ya existe en la tabla knowledge';
    END IF;
END $$;

COMMIT;