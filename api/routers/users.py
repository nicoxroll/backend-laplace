from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

# Importaciones internas
from database.db import get_db
from models import User, UserSettings, Chat
# Importar el esquema Pydantic correcto de schemas.py
from schemas import UserSettingsResponse

router = APIRouter()

# Modelos Pydantic para validación y respuestas
# Actualizar la clase UserResponse para usar Pydantic V2
class UserResponse(BaseModel):
    id: int
    provider_user_id: str
    provider: str
    username: str
    email: Optional[str]
    name: Optional[str]
    avatar: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {
        "from_attributes": True  # Reemplaza orm_mode=True
    }

class UserCreate(BaseModel):
    provider_user_id: str
    provider: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None

class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None

# Añadir esta clase Pydantic dentro de users.py
class UserSettingsResponse(BaseModel):
    user_id: int
    theme: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True  # Nuevo en Pydantic v2, reemplaza orm_mode
    }

# Endpoints
@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/by-provider/{provider}/{provider_user_id}", response_model=UserResponse)
async def get_user_by_provider(
    provider: str, 
    provider_user_id: str, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.provider == provider,
        User.provider_user_id == provider_user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar si el usuario ya existe
    existing_user = db.query(User).filter(
        (User.provider_user_id == user.provider_user_id)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Crear nuevo usuario
    db_user = User(
        provider_user_id=user.provider_user_id,
        provider=user.provider,
        username=user.username,
        email=user.email,
        name=user.name,
        avatar=user.avatar
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Crear configuración por defecto
    settings = UserSettings(user_id=db_user.id)
    db.add(settings)
    db.commit()
    
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Actualizar solo los campos proporcionados
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/{user_id}/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    user_id: int, 
    settings_update: UserSettingsUpdate, 
    db: Session = Depends(get_db)
):
    # Verificar que el usuario existe
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Obtener o crear configuración
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
    
    # Actualizar configuración
    update_data = settings_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings

@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.get("/{user_id}/stats", response_model=dict)
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    # Verificar que el usuario existe
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Obtener estadísticas del usuario
    chat_count = db.query(func.count()).select_from(Chat).filter(Chat.user_id == user_id).scalar()
    
    return {
        "username": user.username,
        "chat_count": chat_count or 0,
        "member_since": user.created_at,
    }