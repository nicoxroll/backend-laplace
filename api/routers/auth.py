# api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from database.db import get_db
from services.auth_service import AuthService
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
import requests

# Usar los schemas de api/schemas.py en lugar de definirlos aquí
from schemas import AuthRequest, AuthResponse  # Si existen en tu schema.py
from models import User  # Añade esta importación que falta
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()

@router.post("/{provider}/callback")
async def auth_callback(
    provider: str,
    auth_data: AuthRequest = Body(...),
    db: Session = Depends(get_db)
):
    try:
        if provider not in ["github", "gitlab"]:
            raise HTTPException(status_code=400, detail="Unsupported provider")
            
        # Log de datos recibidos
        print(f"Procesando solicitud para provider: {provider}")
        print(f"Datos recibidos: {auth_data}")
            
        user = await auth_service.register_or_login_user(
            db, 
            provider, 
            auth_data.provider_user_id,
            auth_data.username,
            auth_data.email,
            auth_data.name,
            auth_data.avatar
        )
        
        return AuthResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            avatar=user.avatar,
            provider=user.provider
        )
    except Exception as e:
        # Log detallado del error
        import traceback
        print(f"ERROR en auth_callback: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# Mantén la ruta GET por compatibilidad
@router.get("/{provider}/callback")
async def auth_callback_get(
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

@router.post("/token/exchange", response_model=dict)
async def exchange_token(
    provider: str = Body(...),
    oauth_token: str = Body(...),
    db: Session = Depends(get_db)
):
    # Verificar el token OAuth con el proveedor
    user = None
    
    try:
        # Buscar usuario por proveedor/token
        if provider == "github":
            user_response = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {oauth_token}"}
            )
            if user_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid GitHub OAuth token")
                
            provider_user = user_response.json()
            provider_user_id = str(provider_user.get("id"))
            
        elif provider == "gitlab":
            user_response = requests.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {oauth_token}"}
            )
            if user_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid GitLab OAuth token")
                
            provider_user = user_response.json()
            provider_user_id = str(provider_user.get("id"))
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
            
        # Buscar al usuario en la base de datos
        user = db.query(User).filter(
            User.provider == provider,
            User.provider_user_id == provider_user_id
        ).first()
            
        if not user:
            print(f"Usuario no encontrado para {provider} con ID {provider_user_id}")
            # Opcional: crear el usuario automáticamente si no existe
            # Pero por ahora solo mostramos información detallada sobre el error
            raise HTTPException(status_code=404, detail=f"User not found for {provider} with ID {provider_user_id}")
        
        # Generar token JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expires = datetime.utcnow() + access_token_expires
        
        payload = {
            "sub": user.username,
            "user_id": user.id,
            "exp": expires
        }
        
        access_token = jwt.encode(
            payload, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires": expires.isoformat()
        }
    except Exception as e:
        print(f"Error exchanging token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
