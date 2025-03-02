from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from database.db import Base


class TimestampMixin:
    """Mixin that adds timestamp columns to a model."""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BaseModel(Base, TimestampMixin):
    """Base model with common fields and functionality."""
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)


class User(BaseModel):
    """User account information."""
    __tablename__ = "users"
    
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    
    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    knowledge_items = relationship("Knowledge", back_populates="user", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="user", cascade="all, delete-orphan")


class KnowledgeBase(BaseModel):
    """Collection of knowledge vectors organized as a knowledge base."""
    __tablename__ = "knowledge_bases"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    vector_config = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="knowledge_bases")
    agents = relationship("Agent", back_populates="knowledge_base")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'id', name='uq_user_knowledge_base'),
    )


class Agent(BaseModel):
    """AI agent configuration and metadata."""
    __tablename__ = "agents"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    name = Column(String, nullable=False)
    is_private = Column(Boolean, default=True)
    description = Column(Text)
    api_url = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    chats = relationship("Chat", back_populates="agent", cascade="all, delete-orphan")
    knowledge_base = relationship("KnowledgeBase", back_populates="agents")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'id', name='uq_user_agent'),
        UniqueConstraint('user_id', 'knowledge_id', name='uq_user_agent_knowledge'),
    )


class Knowledge(BaseModel):
    """Individual knowledge item or document."""
    __tablename__ = "knowledge"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    vector_ids = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="knowledge_items")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'id', name='uq_user_knowledge'),
    )


class AgentKnowledge(Base, TimestampMixin):
    """Association between agents and knowledge items."""
    __tablename__ = "agent_knowledge"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id"), primary_key=True)


class AnalysisResult(Base):
    """Stores results of agent analysis operations."""
    __tablename__ = "analysis_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    knowledge_ids = Column(JSON)
    repo_ids = Column(JSON)
    query = Column(String)
    response = Column(String)
    context_used = Column(JSON)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class Repository(BaseModel):
    """Source code repository information."""
    __tablename__ = "repositories"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    repo_url = Column(String, unique=True, nullable=False)
    name = Column(String)
    platform = Column(String, nullable=False)
    last_indexed = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="repositories")


class Chat(BaseModel):
    """Chat session between user and agent."""
    __tablename__ = "chats"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    title = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual message within a chat."""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")


class UserSettings(Base, TimestampMixin):
    """User preferences and settings."""
    __tablename__ = "user_settings"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    theme = Column(String, default="light")
    language = Column(String, default="en")
    
    # Relationships
    user = relationship("User", back_populates="settings")