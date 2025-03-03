ALTER TABLE users ADD COLUMN IF NOT EXISTS provider VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_user_id VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR;

-- Añadir un índice para búsqueda rápida por provider y provider_user_id
CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider, provider_user_id);