CREATE UNIQUE INDEX idx_agents_user_id_id ON agents(user_id, id);
CREATE UNIQUE INDEX idx_knowledge_user_id_id ON knowledge(user_id, id);
CREATE UNIQUE INDEX idx_agent_knowledge_user_id_agent_id_knowledge_id ON agent_knowledge(user_id, agent_id, knowledge_id);
