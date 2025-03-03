-- 005_create_system_agents.sql
BEGIN;

-- Paso 1: Añadir columnas necesarias
ALTER TABLE knowledge_bases 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS is_system_base BOOLEAN DEFAULT FALSE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_system_user BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

ALTER TABLE agents
ADD COLUMN IF NOT EXISTS is_system_agent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS api_path VARCHAR(255),
ADD COLUMN IF NOT EXISTS model VARCHAR(50) DEFAULT 'gpt-4o';

-- Paso 2: Asegurarnos que existe el usuario sistema
DO $$
DECLARE 
    system_user_id INTEGER;
BEGIN
    -- Buscar o crear usuario sistema
    SELECT id INTO system_user_id FROM users WHERE username = 'sistema';
    
    IF system_user_id IS NULL THEN
        -- Crear usuario si no existe
        INSERT INTO users (username, email, provider, provider_user_id, is_system_user, is_superuser)
        VALUES ('sistema', 'sistema@laplace.ai', 'system', 'system', TRUE, TRUE)
        RETURNING id INTO system_user_id;
    ELSE
        -- Actualizar atributos si el usuario ya existe
        UPDATE users 
        SET is_system_user = TRUE, is_superuser = TRUE 
        WHERE id = system_user_id;
    END IF;

    -- Crear los pares de knowledge_base y agente uno por uno
    -- 1. General Knowledge y Asistente General
    WITH kb_insert AS (
        INSERT INTO knowledge_bases (user_id, name, description, vector_config, is_system_base)
        SELECT
            system_user_id,
            'General Knowledge',
            'Conocimiento general para consultas diversas',
            '{"type": "system"}'::jsonb,
            TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM knowledge_bases 
            WHERE user_id = system_user_id AND name = 'General Knowledge'
        )
        RETURNING id
    ),
    kb_select AS (
        SELECT id FROM knowledge_bases 
        WHERE user_id = system_user_id AND name = 'General Knowledge'
    )
    INSERT INTO agents (user_id, knowledge_id, name, description, api_path, is_system_agent, model)
    SELECT
        system_user_id,
        COALESCE((SELECT id FROM kb_insert), (SELECT id FROM kb_select)),
        'Asistente General',
        'Conocimiento general para consultas diversas',
        '/system/general',
        TRUE,
        'gpt-4o'
    WHERE NOT EXISTS (
        SELECT 1 FROM agents 
        WHERE user_id = system_user_id AND name = 'Asistente General'
    );

    -- 2. Programming Assistant y Asistente de Programación
    WITH kb_insert AS (
        INSERT INTO knowledge_bases (user_id, name, description, vector_config, is_system_base)
        SELECT
            system_user_id,
            'Programming Assistant',
            'Base de conocimiento para programación',
            '{"type": "system"}'::jsonb,
            TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM knowledge_bases 
            WHERE user_id = system_user_id AND name = 'Programming Assistant'
        )
        RETURNING id
    ),
    kb_select AS (
        SELECT id FROM knowledge_bases 
        WHERE user_id = system_user_id AND name = 'Programming Assistant'
    )
    INSERT INTO agents (user_id, knowledge_id, name, description, api_path, is_system_agent, model)
    SELECT
        system_user_id,
        COALESCE((SELECT id FROM kb_insert), (SELECT id FROM kb_select)),
        'Asistente de Programación',
        'Especialista en desarrollo de software',
        '/system/programming',
        TRUE,
        'gpt-4o'
    WHERE NOT EXISTS (
        SELECT 1 FROM agents 
        WHERE user_id = system_user_id AND name = 'Asistente de Programación'
    );

    -- 3. Data Analysis y Analista de Datos
    WITH kb_insert AS (
        INSERT INTO knowledge_bases (user_id, name, description, vector_config, is_system_base)
        SELECT
            system_user_id,
            'Data Analysis',
            'Datos y análisis estadístico',
            '{"type": "system"}'::jsonb,
            TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM knowledge_bases 
            WHERE user_id = system_user_id AND name = 'Data Analysis'
        )
        RETURNING id
    ),
    kb_select AS (
        SELECT id FROM knowledge_bases 
        WHERE user_id = system_user_id AND name = 'Data Analysis'
    )
    INSERT INTO agents (user_id, knowledge_id, name, description, api_path, is_system_agent, model)
    SELECT
        system_user_id,
        COALESCE((SELECT id FROM kb_insert), (SELECT id FROM kb_select)),
        'Analista de Datos',
        'Experto en análisis de datos',
        '/system/data',
        TRUE,
        'gpt-4o'
    WHERE NOT EXISTS (
        SELECT 1 FROM agents 
        WHERE user_id = system_user_id AND name = 'Analista de Datos'
    );

    RAISE NOTICE 'Configuración de agentes del sistema completada con éxito';
END $$;

COMMIT;