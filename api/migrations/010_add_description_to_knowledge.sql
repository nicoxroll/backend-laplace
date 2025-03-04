-- 010_add_description_to_knowledge.sql
BEGIN;

-- Añadir columna description a la tabla knowledge
ALTER TABLE knowledge ADD COLUMN description TEXT;

-- Mensaje informativo
DO $$ 
BEGIN
    RAISE NOTICE 'Columna description añadida a la tabla knowledge';
END $$;

COMMIT;