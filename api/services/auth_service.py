from services.user_service import UserService, UserCreate
from sqlalchemy.orm import Session
import os

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

    # Añade este método que falta:
    async def authenticate_with_provider(self, db: Session, provider: str, code: str):
        """
        Authenticate user with OAuth provider using authorization code
        """
        try:
            if provider == "github":
                # Intercambiar código por token de acceso
                import requests
                response = requests.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": os.environ.get("GITHUB_ID"),
                        "client_secret": os.environ.get("GITHUB_SECRET"),
                        "code": code
                    }
                )
                data = response.json()
                access_token = data.get("access_token")
                
                if not access_token:
                    raise Exception(f"Failed to get access token: {data}")
                    
                # Obtener datos del usuario
                user_response = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                user_data = user_response.json()
                
                # Crear o actualizar usuario
                return await self.register_or_login_user(
                    db,
                    "github",
                    str(user_data.get("id")),
                    user_data.get("login"),
                    user_data.get("email"),
                    user_data.get("name"),
                    user_data.get("avatar_url")
                )
            
            elif provider == "gitlab":
                # Implementación similar para GitLab
                # ...
                pass
            
            else:
                raise Exception(f"Unsupported provider: {provider}")
                
        except Exception as e:
            raise Exception(f"Authentication error: {str(e)}")
