-- Asegúrate que esta tabla exista
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    message_metadata JSONB,  -- Renombrado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON chat_messages(chat_id);