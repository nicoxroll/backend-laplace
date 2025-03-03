# api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from database.db import get_db
from services.auth_service import AuthService
from typing import Optional

# Usar los schemas de api/schemas.py en lugar de definirlos aquí
from schemas import AuthRequest, AuthResponse  # Si existen en tu schema.py

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
