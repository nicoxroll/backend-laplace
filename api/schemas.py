from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# User schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    name: Optional[str] = None

class UserCreate(UserBase):
    provider_user_id: str
    provider: str
    avatar: Optional[str] = None

class UserResponse(UserBase):
    id: int
    provider_user_id: str
    provider: str
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# Agent schemas
class AgentBase(BaseModel):
    name: str
    is_private: bool = True
    is_system_agent: bool = False  # Añadir campo
    description: Optional[str] = None
    api_url: Optional[str] = None

class AgentCreate(AgentBase):
    knowledge_id: int

class AgentResponse(AgentBase):
    id: int
    user_id: int
    knowledge_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Knowledge schemas
class KnowledgeBase(BaseModel):
    name: str
    vector_ids: Optional[Dict[str, Any]] = None

class KnowledgeCreate(KnowledgeBase):
    pass

class KnowledgeResponse(KnowledgeBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Repository schemas
class RepositoryBase(BaseModel):
    repo_url: str
    platform: str
    name: Optional[str] = None

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryResponse(RepositoryBase):
    id: int
    user_id: int
    last_indexed: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Chat schemas
class ChatBase(BaseModel):
    agent_id: Optional[int] = None
    title: Optional[str] = None

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Agent Knowledge schemas
class AgentKnowledgeBase(BaseModel):
    agent_id: int
    knowledge_id: int

class AgentKnowledgeCreate(AgentKnowledgeBase):
    pass

class AgentKnowledgeResponse(AgentKnowledgeBase):
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Analysis schemas
class AnalysisRequest(BaseModel):
    agent_id: Optional[int] = None
    query: str
    knowledge_ids: Optional[List[int]] = None
    repo_ids: Optional[List[int]] = None

class AnalysisResponse(BaseModel):
    id: UUID
    query: str
    response: str
    context_used: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Knowledge Base schemas
class KnowledgeBaseBase(BaseModel):
    name: str
    vector_config: Optional[Dict[str, Any]] = None

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    vector_config: Optional[Dict[str, Any]] = None

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    vector_config: Optional[Dict[str, Any]] = None

class KnowledgeBaseResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    vector_config: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

# User Settings schemas
class UserSettingsBase(BaseModel):
    theme: Optional[str] = "light"
    language: Optional[str] = "en"

class UserSettingsCreate(UserSettingsBase):
    pass

class UserSettingsResponse(UserSettingsBase):
    user_id: int
    theme: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# Añadir estas clases para autenticación
class AuthRequest(BaseModel):
    provider_user_id: str
    provider: str
    username: str
    email: Optional[str] = ""  # Proporcionar valores por defecto
    name: Optional[str] = ""
    avatar: Optional[str] = ""
    access_token: Optional[str] = None

class AuthResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    provider: str
    
    model_config = {
        "from_attributes": True
    }

# Añadir al final del archivo

class KnowledgeBase(BaseModel):
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    is_system_base: bool = False
    vector_config: Optional[Dict[str, Any]] = None

class KnowledgeBaseResponse(KnowledgeBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class Knowledge(BaseModel):
    name: str
    content_hash: str
    vector_ids: Optional[Dict[str, Any]] = None

class KnowledgeResponse(Knowledge):
    id: int
    user_id: int
    base_id: Optional[int] = None
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }
