from sqlalchemy.orm import Session
from models import User  # Importar desde models, no desde schemas
from schemas import UserCreate  # Importar esquema desde schemas
from typing import Optional

class UserService:
    def find_user_by_provider_user_id(self, db: Session, provider: str, provider_user_id: str):
        return db.query(User).filter(
            User.provider == provider,
            User.provider_user_id == str(provider_user_id)
        ).first()
        
    def create_user(self, db: Session, user_data: UserCreate):
        try:
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
        except Exception as e:
            db.rollback()
            print(f"Error al crear usuario: {e}")
            import traceback
            print(traceback.format_exc())
            raise Exception(f"Error al crear usuario: {str(e)}")
