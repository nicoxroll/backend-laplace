from api.models import Agent, AgentKnowledge

# Usuario 1 crea agentes privados
agente1 = Agent(user_id=1, name="Mi Agente Privado", is_private=True)
agente2 = Agent(user_id=1, name="Agente Compartido", is_private=False)

# Usuario 1 vincula conocimiento a sus agentes
link1 = AgentKnowledge(user_id=1, agent_id=1, knowledge_id=54)
link2 = AgentKnowledge(user_id=1, agent_id=2, knowledge_id=54)

# Usuario 2 intenta acceder (fallará)
try:
    link3 = AgentKnowledge(user_id=2, agent_id=1, knowledge_id=54)
except Exception:
    print("Error: Violación de restricción de usuario")