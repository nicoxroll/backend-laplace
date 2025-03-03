from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List

from database.db import get_db
from models import Agent, AgentKnowledge, User
from schemas import AgentResponse
from dependencies.auth import get_current_user

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

@router.get("/", response_model=List[AgentResponse])
async def get_available_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los agentes disponibles para el usuario:
    - Sus agentes privados
    - Agentes del sistema
    """
    agents = db.query(Agent).filter(
        # El agente pertenece al usuario O es un agente del sistema
        ((Agent.user_id == current_user.id) | (Agent.is_system_agent == True))
    ).all()
    return agents

@router.get("/system", response_model=List[AgentResponse])
async def get_system_agents(db: Session = Depends(get_db)):
    """
    Obtiene todos los agentes del sistema disponibles para cualquier usuario.
    No requiere autenticación para permitir obtenerlos en la página inicial.
    """
    agents = db.query(Agent).filter(Agent.is_system_agent == True).all()
    return agents

@router.get("/system/{slug}", response_model=AgentResponse)
async def get_system_agent_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Obtiene un agente del sistema específico por su slug
    """
    agent = db.query(Agent).filter(
        Agent.is_system_agent == True,
        Agent.slug == slug
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agente del sistema no encontrado")
    
    return agent

@router.get("/user/{user_id}", response_model=List[AgentResponse])
async def get_user_agents(
    user_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los agentes personalizados de un usuario.
    """
    # Verificar permisos (solo el mismo usuario o admin)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver estos agentes")
    
    agents = db.query(Agent).filter(
        Agent.user_id == user_id,
        Agent.is_system_agent == False
    ).all()
    
    return agents