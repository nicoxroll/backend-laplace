from services.user_service import UserService, UserCreate
from sqlalchemy.orm import Session

# Asegúrate que tu services/auth_service.py tenga esta configuración
class AuthService:
    def __init__(self):
        self.user_service = UserService()
    
    async def register_or_login_user(self, db: Session, provider: str, 
                                provider_user_id: str, username: str, 
                                email: str = None, name: str = None, 
                                avatar: str = None):
        """
        Register a new user or login an existing user
        """
        # Check if user exists
        existing_user = self.user_service.find_user_by_provider_user_id(
            db, provider, provider_user_id
        )
        
        if not existing_user:
            # Create new user
            user_create = UserCreate(
                provider_user_id=str(provider_user_id),
                provider=provider,
                username=username,
                email=email,
                name=name,
                avatar=avatar
            )
            return self.user_service.create_user(db, user_create)
        
        return existing_user
    