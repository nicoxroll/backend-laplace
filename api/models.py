from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
import uuid
from datetime import datetime
from database.db import Base

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=True)
    username = Column(String(50), unique=True, nullable=False)
    provider = Column(String(50))
    provider_user_id = Column(String(100))
    name = Column(String(100))
    avatar = Column(String(255))
    is_system_user = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="user", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    knowledge_items = relationship("Knowledge", back_populates="user")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),
    )

class KnowledgeBase(BaseModel):
    __tablename__ = "knowledge_bases"
    
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_system_base = Column(Boolean, default=False)
    
    # Relación existente
    knowledge_items = relationship("Knowledge", back_populates="base")
    
    # Agregar esta relación que falta
    agents = relationship("Agent", back_populates="knowledge_base")
    
    user = relationship("User", back_populates="knowledge_bases")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_kb_name'),
    )

class Agent(BaseModel):
    __tablename__ = "agents"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    api_path = Column(String(255))
    model = Column(String(50), default="gpt-4o")
    is_private = Column(Boolean, default=True)
    is_system_agent = Column(Boolean, default=False)

    user = relationship("User", back_populates="agents")
    knowledge_base = relationship("KnowledgeBase", back_populates="agents")
    chats = relationship("Chat", back_populates="agent", cascade="all, delete-orphan")

class Knowledge(BaseModel):
    __tablename__ = "knowledge"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True)
    content_hash = Column(String(64), nullable=False)
    vector_ids = Column(JSON, nullable=True)
    
    # Esta relación ya estaba correcta
    user = relationship("User", back_populates="knowledge_items")
    base = relationship("KnowledgeBase", back_populates="knowledge_items")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_knowledge_name'),
    )

class AgentKnowledge(Base, TimestampMixin):
    __tablename__ = "agent_knowledge"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id"), primary_key=True)
    access_level = Column(String(20), default="read")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    knowledge_ids = Column(JSON)
    query = Column(Text)
    response = Column(Text)
    context_used = Column(JSON)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="analysis_results")

class Repository(BaseModel):
    __tablename__ = "repositories"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    repo_url = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    platform = Column(String(50), nullable=False)
    last_indexed = Column(DateTime)
    indexing_status = Column(String(20), default="pending")

    user = relationship("User", back_populates="repositories")
    analysis_results = relationship("AnalysisResult", back_populates="repository")

class Chat(BaseModel):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Explicitly an Integer, not UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")

class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Renombrado de metadata a message_metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")

class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    theme = Column(String(20), default="light")
    language = Column(String(10), default="en")
    notification_preferences = Column(JSON, default={"email": True, "push": True})

    user = relationship("User", back_populates="settings")