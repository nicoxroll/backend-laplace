import os
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .user_service import UserService, UserCreate

load_dotenv()

class AuthService:
    def __init__(self):
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
        self.github_secret = os.getenv("GITHUB_SECRET", "")
        self.gitlab_client_id = os.getenv("GITLAB_CLIENT_ID", "")
        self.gitlab_secret = os.getenv("GITLAB_SECRET", "")
        self.user_service = UserService()
        self.app_url = os.getenv("APP_URL", "http://localhost:8000")

    async def authenticate_with_provider(self, db: Session, provider: str, code: str):
        try:
            if provider == "github":
                user_data = await self.authenticate_with_github(code)
            elif provider == "gitlab":
                user_data = await self.authenticate_with_gitlab(code)
            else:
                raise ValueError("Unsupported provider")
            
            # Check if user exists, if not create them
            existing_user = self.user_service.find_user_by_provider_user_id(
                db, provider, user_data["id"]
            )
            
            if not existing_user:
                user_create = UserCreate(
                    provider_user_id=str(user_data["id"]),
                    provider=provider,
                    username=user_data.get("login") or user_data.get("username"),
                    email=user_data.get("email"),
                    name=user_data.get("name"),
                    avatar=user_data.get("avatar_url") or user_data.get("avatar")
                )
                return self.user_service.create_user(db, user_create)
            
            return existing_user
                
        except Exception as error:
            print(f"Authentication error: {error}")
            raise error
    
    async def authenticate_with_github(self, code: str):
        # Validate with GitHub client ID and secret
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": self.github_client_id,
                "client_secret": self.github_secret,
                "code": code
            },
            headers={"Accept": "application/json"}
        )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ValueError("Failed to obtain access token from GitHub")
            
        # Get user data with the token
        user_response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )
        
        return user_response.json()
        
    async def authenticate_with_gitlab(self, code: str):
        # Validate with GitLab client ID and secret
        token_response = requests.post(
            "https://gitlab.com/oauth/token",
            json={
                "client_id": self.gitlab_client_id,
                "client_secret": self.gitlab_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{self.app_url}/auth/gitlab/callback"
            }
        )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ValueError("Failed to obtain access token from GitLab")
            
        # Get user data with the token
        user_response = requests.get(
            "https://gitlab.com/api/v4/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        return user_response.json()
