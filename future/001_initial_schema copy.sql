CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR NOT NULL UNIQUE,
  username VARCHAR NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agents (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name VARCHAR NOT NULL,
  is_private BOOLEAN DEFAULT TRUE,
  description TEXT,
  api_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, id)
);

CREATE TABLE knowledge (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name VARCHAR NOT NULL,
  vector_ids JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, id)
);

CREATE TABLE agent_knowledge (
  user_id INTEGER NOT NULL,
  agent_id INTEGER NOT NULL,
  knowledge_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, agent_id, knowledge_id),
  FOREIGN KEY (user_id, agent_id) REFERENCES agents(user_id, id),
  FOREIGN KEY (user_id, knowledge_id) REFERENCES knowledge(user_id, id)
);

CREATE TABLE analysis_results (
  id UUID PRIMARY KEY,
  agent_id INTEGER REFERENCES agents(id),
  knowledge_ids JSON,
  repo_ids JSON,
  query VARCHAR,
  response VARCHAR,
  context_used JSON,
  user_id INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE repositories (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  repo_url VARCHAR NOT NULL UNIQUE,
  name VARCHAR,
  platform VARCHAR NOT NULL,
  last_indexed TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chats (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  agent_id INTEGER REFERENCES agents(id),
  title VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_settings (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  theme VARCHAR DEFAULT 'light',
  language VARCHAR DEFAULT 'en',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge_bases (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name VARCHAR(100) NOT NULL,
  vector_config JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_user_knowledge ON knowledge_bases(user_id, id);

ALTER TABLE agents
ADD COLUMN knowledge_id INTEGER NOT NULL REFERENCES knowledge_bases(id);

CREATE UNIQUE INDEX uq_user_agent_knowledge ON agents(user_id, knowledge_id);

