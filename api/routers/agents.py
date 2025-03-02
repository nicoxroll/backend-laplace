from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import Agent, AgentKnowledge
from database.db import get_db

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/{agent_id}/knowledge/{knowledge_id}")
async def link_knowledge_to_agent(
    user_id: int,
    agent_id: int,
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Verificar existencia y pertenencia
    agent = await db.execute(
        select(Agent)
        .where(Agent.user_id == user_id)
        .where(Agent.id == agent_id)
    )
    agent = agent.scalar_one_or_none()
    
    knowledge = await db.execute(
        select(Knowledge)
        .where(Knowledge.user_id == user_id)
        .where(Knowledge.id == knowledge_id)
    )
    knowledge = knowledge.scalar_one_or_none()
    
    if not agent or not knowledge:
        raise HTTPException(404, "Recurso no encontrado o acceso denegado")
    
    try:
        link = AgentKnowledge(
            user_id=user_id,
            agent_id=agent_id,
            knowledge_id=knowledge_id
        )
        db.add(link)
        await db.commit()
        return {"message": "Conocimiento vinculado exitosamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(400, "Error al vincular recursos")