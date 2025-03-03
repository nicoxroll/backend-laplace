from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from database.db import get_db
from models import KnowledgeBase, User
from schemas import KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate
from dependencies.auth import get_current_user

router = APIRouter(tags=["user_knowledge"])

@router.get("/{user_id}/knowledge", response_model=List[KnowledgeBaseResponse])
async def get_user_knowledge_bases(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las bases de conocimiento de un usuario
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a estas bases de conocimiento")
    
    knowledge_bases = db.query(KnowledgeBase).filter(KnowledgeBase.user_id == user_id).all()
    return knowledge_bases

@router.get("/{user_id}/knowledge/{knowledge_id}", response_model=KnowledgeBaseResponse)
async def get_user_knowledge_base(
    user_id: int,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene una base de conocimiento específica de un usuario
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta base de conocimiento")
    
    knowledge_base = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_id,
        KnowledgeBase.user_id == user_id
    ).first()
    
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    return knowledge_base

@router.post("/{user_id}/knowledge", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    user_id: int,
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva base de conocimiento para un usuario
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para crear bases de conocimiento para este usuario")
    
    # Verificar si ya existe una base de conocimiento con el mismo nombre para este usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user_id,
        KnowledgeBase.name == knowledge_base.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una base de conocimiento con este nombre")
    
    new_kb = KnowledgeBase(
        user_id=user_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        vector_config=knowledge_base.vector_config or {}
    )
    
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    return new_kb

@router.put("/{user_id}/knowledge/{knowledge_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    user_id: int,
    knowledge_id: int,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza una base de conocimiento existente
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta base de conocimiento")
    
    # Verificar si la base de conocimiento existe y pertenece al usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_id,
        KnowledgeBase.user_id == user_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    # Actualizar los campos proporcionados
    if knowledge_base.name is not None:
        # Verificar si el nuevo nombre ya existe para otro conocimiento del usuario
        name_exists = db.query(KnowledgeBase).filter(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.name == knowledge_base.name,
            KnowledgeBase.id != knowledge_id
        ).first()
        
        if name_exists:
            raise HTTPException(status_code=409, detail="Ya existe otra base de conocimiento con este nombre")
        
        existing.name = knowledge_base.name
    
    if knowledge_base.description is not None:
        existing.description = knowledge_base.description
    
    if knowledge_base.vector_config is not None:
        existing.vector_config = knowledge_base.vector_config
    
    db.commit()
    db.refresh(existing)
    
    return existing

@router.delete("/{user_id}/knowledge/{knowledge_id}", status_code=204)
async def delete_knowledge_base(
    user_id: int,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina una base de conocimiento
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta base de conocimiento")
    
    # Verificar si la base de conocimiento existe y pertenece al usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_id,
        KnowledgeBase.user_id == user_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    # Eliminar la base de conocimiento
    db.delete(existing)
    db.commit()
    
    return None
