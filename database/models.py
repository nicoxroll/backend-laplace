from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    provider_user_id = Column(String, unique=True, index=True)
    provider = Column(String)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    name = Column(String)
    avatar = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
