-- 005_create_system_agents.sql
BEGIN;

-- Paso 1: Añadir columnas necesarias (sin slug)
ALTER TABLE knowledge_bases 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS is_system_base BOOLEAN DEFAULT FALSE;  -- Eliminado slug

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_system_user BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

ALTER TABLE agents
ADD COLUMN IF NOT EXISTS is_system_agent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS api_path VARCHAR(255),
ADD COLUMN IF NOT EXISTS model VARCHAR(50) DEFAULT 'gpt-4o';  -- Eliminado slug

-- Paso 2: Crear usuario del sistema (sin cambios)
INSERT INTO users (username, email, provider, provider_user_id, is_system_user, is_superuser)
SELECT 
    'sistema', 
    'sistema@laplace.ai', 
    'system', 
    'system', 
    TRUE, 
    TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'sistema'
);

-- Paso 3: Crear knowledge bases del sistema (sin slug)
WITH system_user AS (
    SELECT id FROM users WHERE username = 'sistema'
),
new_knowledge AS (
    INSERT INTO knowledge_bases (user_id, name, description, vector_config, is_system_base)
    SELECT
        su.id,
        data.name,
        data.description,
        '{"type": "system"}'::jsonb,
        TRUE
    FROM system_user su
    CROSS JOIN (VALUES
        ('General Knowledge', 'Conocimiento general para consultas diversas'),
        ('Programming Assistant', 'Base de conocimiento para programación'),
        ('Data Analysis', 'Datos y análisis estadístico')
    ) AS data(name, description)
    ON CONFLICT (user_id, name) DO NOTHING  -- Usamos name para el conflicto
    RETURNING id  -- Ya no se retorna slug
)

-- Paso 4: Insertar agentes del sistema (sin slug)
INSERT INTO agents (user_id, knowledge_id, name, description, api_path, is_system_agent, model)
SELECT
    su.id,
    nk.id,
    data.name,
    data.description,
    '/system/' || lower(replace(data.name, ' ', '-')),  -- Generamos api_path desde name
    TRUE,
    'gpt-4o'
FROM system_user su
JOIN new_knowledge nk ON true
JOIN (VALUES
    ('Asistente General', 'Conocimiento general para consultas diversas'),
    ('Asistente de Programación', 'Base de conocimiento para programación'),
    ('Analista de Datos', 'Datos y análisis estadístico')
) AS data(name, description) ON nk.id = nk.id  -- Lógica de join simplificada
ON CONFLICT (user_id, name) DO NOTHING;  -- Usamos name para el conflicto

COMMIT;