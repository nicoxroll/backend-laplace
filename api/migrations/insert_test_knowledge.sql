-- Crear 4 registros de knowledge para pruebas
DO $$
DECLARE
    system_user_id INTEGER;
    knowledge_base_id INTEGER;
BEGIN
    -- Obtener ID del usuario sistema
    SELECT id INTO system_user_id FROM users WHERE username = 'sistema';
    
    -- Obtener ID de la primera base de conocimiento del sistema
    SELECT id INTO knowledge_base_id FROM knowledge_bases 
    WHERE user_id = system_user_id AND is_system_base = true
    LIMIT 1;

    -- Insertar 4 items de conocimiento de prueba
    INSERT INTO knowledge (user_id, name, vector_ids, content_hash, base_id) 
    VALUES 
        (system_user_id, 'Prueba de Conocimiento 1', '{"vector": "001"}', md5('contenido1'), knowledge_base_id),
        (system_user_id, 'Prueba de Conocimiento 2', '{"vector": "002"}', md5('contenido2'), knowledge_base_id),
        (system_user_id, 'Prueba de Conocimiento 3', '{"vector": "003"}', md5('contenido3'), knowledge_base_id),
        (system_user_id, 'Prueba de Conocimiento 4', '{"vector": "004"}', md5('contenido4'), knowledge_base_id);

    RAISE NOTICE 'Se han creado 4 registros de conocimiento de prueba para el usuario %', system_user_id;
END $$;