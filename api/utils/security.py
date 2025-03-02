from models import AgentKnowledge
from sqlalchemy.ext.asyncio import AsyncSession

async def validate_agent_knowledge_access(
    user_id: int,
    agent_id: int,
    knowledge_id: int,
    db: AsyncSession
):
    # Verificar triple pertenencia
    exists = await db.execute(
        select(AgentKnowledge)
        .where(AgentKnowledge.user_id == user_id)
        .where(AgentKnowledge.agent_id == agent_id)
        .where(AgentKnowledge.knowledge_id == knowledge_id)
    )
    if not exists.scalar_one_or_none():
        raise HTTPException(403, "Acceso no autorizado al conocimiento")