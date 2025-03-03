from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from database.db import get_db
from models import Agent, KnowledgeBase, User
from schemas import AgentResponse
from dependencies.auth import get_current_user, get_optional_user

router = APIRouter(tags=["system_agents"])

class QueryRequest(BaseModel):
    query: str
    options: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    agent_id: int
    agent_name: str
    query: str
    response: str

@router.get("/", response_model=List[AgentResponse])
async def get_system_agents(db: Session = Depends(get_db)):
    """
    Obtiene todos los agentes del sistema disponibles para cualquier usuario.
    No requiere autenticación para permitir obtenerlos en la página inicial.
    """
    agents = db.query(Agent).filter(Agent.is_system_agent == True).all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_system_agent_by_id(agent_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un agente del sistema específico por su ID
    """
    agent = db.query(Agent).filter(
        Agent.is_system_agent == True,
        Agent.id == agent_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agente del sistema no encontrado")
    
    return agent

@router.post("/{agent_id}/query", response_model=QueryResponse)
async def query_system_agent(
    agent_id: int, 
    query_request: QueryRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    """
    Envía una consulta a un agente del sistema
    """
    agent = db.query(Agent).filter(
        Agent.is_system_agent == True,
        Agent.id == agent_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agente del sistema no encontrado")
    
    # Recuperar la base de conocimiento asociada
    knowledge_base = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == agent.knowledge_id
    ).first()
    
    if not knowledge_base:
        raise HTTPException(status_code=500, detail="Base de conocimiento no encontrada para este agente")
    
    # Aquí iría la integración con tu servicio de IA usando el modelo del agente y su base de conocimiento
    # Esta es una implementación de placeholder
    ai_response = process_agent_query(query_request.query, agent, knowledge_base, query_request.options)
    
    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "query": query_request.query,
        "response": ai_response
    }

def process_agent_query(query: str, agent: Agent, knowledge_base: KnowledgeBase, options: Dict[str, Any] = None) -> str:
    """
    Procesa una consulta utilizando el agente y su base de conocimiento.
    Esta es una función placeholder que debería ser reemplazada con tu integración real de IA.
    """
    # Implementar la integración real con el servicio de IA aquí
    return f"Respuesta a '{query}' del agente {agent.name} usando el modelo {agent.model}"
