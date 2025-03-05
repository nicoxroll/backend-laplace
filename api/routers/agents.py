from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List

from database.db import get_db
from models import Agent, Knowledge, AgentKnowledgeItem, User, KnowledgeBase
from schemas import AgentResponse, AgentCreate, AgentUpdate
from dependencies.auth import get_current_user

# Quitar el prefix "/agents" redundante
router = APIRouter()

# Modificar el schema para soportar múltiples knowledge IDs
class AgentUpdate(AgentCreate):
    knowledge_ids: List[int] = []  # Lista de IDs de documentos de conocimiento

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
        ((Agent.user_id == current_user.id) | (Agent.is_system_agent == True))
    ).all()
    
    results = []
    for agent in agents:
        # Inicializar listas para IDs y nombres
        knowledge_ids = []
        knowledge_names = []
        
        # CASO 1: Para agentes que tienen knowledge_id directo (agentes del sistema)
        if hasattr(agent, "knowledge_id") and agent.knowledge_id:
            # Buscar en knowledge_bases (para agentes del sistema)
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == agent.knowledge_id).first()
            if kb:
                knowledge_ids.append(kb.id)
                knowledge_names.append(kb.name)
                print(f"Agente {agent.name}: base de conocimiento directa: {kb.name}")
        
        # CASO 2: Para todos los agentes - conocimientos a través de agent_knowledge_items
        knowledge_items = db.query(Knowledge).join(
            AgentKnowledgeItem,
            Knowledge.id == AgentKnowledgeItem.knowledge_id
        ).filter(
            AgentKnowledgeItem.agent_id == agent.id
        ).all()
        
        # Añadir estos items a nuestra lista
        for item in knowledge_items:
            # Evitar duplicados
            if item.id not in knowledge_ids:
                knowledge_ids.append(item.id)
                knowledge_names.append(item.name)
                print(f"Agente {agent.name}: conocimiento asociado: {item.name}")
        
        # Construir el objeto de respuesta
        agent_dict = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "is_private": agent.is_private,
            "is_system_agent": agent.is_system_agent,
            "api_path": agent.api_path,
            "created_at": agent.created_at.isoformat() if agent.created_at else "",
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else "",
            "user_id": str(agent.user_id),
            "knowledge_ids": knowledge_ids,
            "knowledge_base_name": ", ".join(knowledge_names) if knowledge_names else "Ninguno",
            "associated_knowledge": knowledge_names
        }
        
        results.append(agent_dict)
    
    return results

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
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permisos
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a estos datos")
        
    agents = db.query(Agent).filter(Agent.user_id == user_id).all()
    results = []
    
    for agent in agents:
        # Inicializar listas para IDs y nombres
        knowledge_ids = []
        knowledge_names = []
        
        # CASO 1: Agentes del sistema con knowledge_id directo
        if agent.is_system_agent and hasattr(agent, "knowledge_id") and agent.knowledge_id:
            knowledge = db.query(Knowledge).filter(Knowledge.id == agent.knowledge_id).first()
            if knowledge:
                knowledge_ids.append(knowledge.id)
                knowledge_names.append(knowledge.name)
        
        # CASO 2: Todos los agentes - buscar en tabla de unión AgentKnowledgeItem
        knowledge_items = db.query(Knowledge).join(
            AgentKnowledgeItem,
            Knowledge.id == AgentKnowledgeItem.knowledge_id
        ).filter(
            AgentKnowledgeItem.agent_id == agent.id
        ).all()
        
        if knowledge_items:
            for item in knowledge_items:
                if item.id not in knowledge_ids:  # Evitar duplicados
                    knowledge_ids.append(item.id)
                    knowledge_names.append(item.name)
        
        # Construir respuesta con ambos tipos de asociaciones
        agent_dict = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "is_private": agent.is_private,
            "is_system_agent": agent.is_system_agent,
            "api_path": agent.api_path,  # Cambiar api_url a api_path
            "created_at": agent.created_at.isoformat() if agent.created_at else "",
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else "",
            "user_id": str(agent.user_id),
            "knowledge_ids": knowledge_ids,
            "knowledge_base_name": ", ".join(knowledge_names) if knowledge_names else "Ninguno",
            "associated_knowledge": knowledge_names  # Lista vacía si no hay conocimiento
        }
        
        results.append(agent_dict)
    
    return results

@router.get("/all/{user_id}", response_model=List[AgentResponse])
async def get_all_user_agents(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los agentes disponibles para un usuario específico:
    - Sus agentes personalizados
    - Agentes del sistema
    """
    # Verificar permisos (solo el mismo usuario o admin)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver estos agentes")
    
    # Obtener todos los agentes disponibles para el usuario:
    # - Los que pertenecen al usuario específicamente
    # - Los agentes del sistema (disponibles para todos)
    agents = db.query(Agent).filter(
        (Agent.user_id == user_id) | (Agent.is_system_agent == True)
    ).all()
    
    return agents

@router.get("/me", response_model=List[AgentResponse])
async def get_my_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los agentes personalizados del usuario autenticado.
    Usa implícitamente el token JWT para identificar al usuario.
    """
    agents = db.query(Agent).filter(
        Agent.user_id == current_user.id,
        Agent.is_system_agent == False
    ).all()
    
    return agents

# Modificar el endpoint de creación
@router.post("/me", response_model=AgentResponse)
async def create_my_agent(
    agent: AgentCreate,
    knowledge_ids: List[int] = Body(default=[]),  # Lista separada para mantener compatibilidad
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo agente para el usuario autenticado.
    """
    # Crear el agente sin knowledge_id
    new_agent = Agent(
        user_id=current_user.id,
        name=agent.name,
        description=agent.description,
        is_private=agent.is_private,
        is_system_agent=False,
        api_path=agent.api_path,
        model="gpt-4o"
    )
    
    db.add(new_agent)
    db.flush()  # Para obtener el ID sin hacer commit
    
    # Añadir todos los knowledge_ids como relaciones
    if knowledge_ids:
        # Verificar que los IDs de conocimiento existan y pertenezcan al usuario
        for kid in knowledge_ids:
            k = db.query(Knowledge).filter(
                Knowledge.id == kid,
                Knowledge.user_id == current_user.id
            ).first()
            
            if not k:
                continue  # Ignorar IDs inválidos
                
            # Crear relación entre agente y documento
            agent_knowledge = AgentKnowledgeItem(
                agent_id=new_agent.id,
                knowledge_id=kid
            )
            db.add(agent_knowledge)
    
    db.commit()
    db.refresh(new_agent)
    
    return new_agent

# Modificar el endpoint de actualización
@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentCreate,
    knowledge_ids: List[int] = Body(default=[]),  # Lista separada para mantener compatibilidad
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un agente existente.
    El usuario debe ser propietario del agente.
    """
    print(f"Actualizando agente ID: {agent_id}, knowledge_ids: {knowledge_ids}")
    
    # Verificar que el agente existe y pertenece al usuario
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id,
        Agent.is_system_agent == False
    ).first()
    
    if not agent:
        agent_exists = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent_exists:
            raise HTTPException(status_code=404, detail=f"Agente ID {agent_id} no encontrado")
        else:
            raise HTTPException(
                status_code=403, 
                detail=f"No tienes permisos para editar el agente ID {agent_id}"
            )
    
    # Actualizar campos básicos del agente
    agent.name = agent_update.name
    agent.description = agent_update.description
    agent.is_private = agent_update.is_private
    agent.api_path = agent_update.api_path
    
    # Eliminar relaciones existentes con documentos
    db.query(AgentKnowledgeItem).filter(
        AgentKnowledgeItem.agent_id == agent_id
    ).delete()
    
    # Añadir nuevas relaciones con documentos
    if knowledge_ids:
        for kid in knowledge_ids:
            # Verificar que el documento existe y pertenece al usuario
            k = db.query(Knowledge).filter(
                Knowledge.id == kid,
                Knowledge.user_id == current_user.id
            ).first()
            
            if not k:
                continue  # Ignorar IDs inválidos
                
            # Crear relación entre agente y documento
            agent_knowledge = AgentKnowledgeItem(
                agent_id=agent_id,
                knowledge_id=kid
            )
            db.add(agent_knowledge)
    
    db.commit()
    db.refresh(agent)
    
    return agent

# Añadir endpoint para obtener los documentos de conocimiento asociados a un agente
@router.get("/{agent_id}/knowledge", response_model=List[dict])
async def get_agent_knowledge(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los documentos de conocimiento asociados a un agente."""
    print(f"Obteniendo knowledge para agente {agent_id}")
    
    # Verificar que el agente existe y pertenece al usuario o es del sistema
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        ((Agent.user_id == current_user.id) | (Agent.is_system_agent == True))
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agente no encontrado o sin acceso"
        )
    
    # Obtener documentos asociados
    knowledge_items = db.query(Knowledge).join(
        AgentKnowledgeItem,
        Knowledge.id == AgentKnowledgeItem.knowledge_id
    ).filter(
        AgentKnowledgeItem.agent_id == agent_id
    ).all()
    
    print(f"Knowledge items encontrados: {len(knowledge_items)}")
    
    # Devolver solo los campos necesarios
    result = []
    for item in knowledge_items:
        item_dict = {
            "id": item.id,
            "name": item.name,
            "description": item.description,  # Ahora incluimos la descripción
            "content_hash": item.content_hash,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "user_id": item.user_id
        }
        result.append(item_dict)
    
    return result

@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un agente.
    El usuario debe ser propietario del agente.
    """
    # Buscar el agente y verificar pertenencia
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id,
        Agent.is_system_agent == False  # No permitir eliminar agentes del sistema
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail="Agente no encontrado o no tienes permisos para eliminarlo"
        )
    
    # Eliminar el agente
    db.delete(agent)
    db.commit()
    
    return None