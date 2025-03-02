from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# Agent schemas
class AgentBase(BaseModel):
    name: str
    is_private: bool = True
    description: Optional[str] = None
    api_url: Optional[str] = None

class AgentCreate(AgentBase):
    knowledge_id: int

class AgentResponse(AgentBase):
    id: int
    user_id: int
    knowledge_id: int
    created_at: datetime

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

# Agent Knowledge schemas
class AgentKnowledgeBase(BaseModel):
    agent_id: int
    knowledge_id: int

class AgentKnowledgeCreate(AgentKnowledgeBase):
    pass

class AgentKnowledgeResponse(AgentKnowledgeBase):
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

# Knowledge Base schemas
class KnowledgeBaseBase(BaseModel):
    name: str
    vector_config: Optional[Dict[str, Any]] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

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
    created_at: datetime

    class Config:
        orm_mode = True
