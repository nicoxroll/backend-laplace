from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.db import get_db
from services.auth_service import AuthService
from pydantic import BaseModel

router = APIRouter()
auth_service = AuthService()

class AuthResponse(BaseModel):
    id: int
    username: str
    email: str = None
    name: str = None
    avatar: str = None
    provider: str

@router.get("/{provider}/callback")
async def auth_callback(
    provider: str,
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        if provider not in ["github", "gitlab"]:
            raise HTTPException(status_code=400, detail="Unsupported provider")
            
        user = await auth_service.authenticate_with_provider(db, provider, code)
        
        return AuthResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            avatar=user.avatar,
            provider=user.provider
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
