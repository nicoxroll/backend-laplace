from sqlalchemy.orm import Session
from database.models import User
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    provider_user_id: str
    provider: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None

class UserService:
    def find_user_by_provider_user_id(self, db: Session, provider: str, provider_user_id: str):
        return db.query(User).filter(
            User.provider == provider,
            User.provider_user_id == str(provider_user_id)
        ).first()
        
    def create_user(self, db: Session, user_data: UserCreate):
        user = User(
            provider_user_id=user_data.provider_user_id,
            provider=user_data.provider,
            username=user_data.username,
            email=user_data.email,
            name=user_data.name,
            avatar=user_data.avatar
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
