from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import requests

from database.db import get_db
from models import User
from schemas import UserCreate, TokenResponse
from auth.jwt import create_access_token
from config import settings

router = APIRouter()

# Other routes...

@router.post("/github/callback")
async def github_callback(code: str, request: Request, db: Session = Depends(get_db)):
    # Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI
    }
    headers = {"Accept": "application/json"}
    
    response = requests.post(token_url, data=data, headers=headers)
    token_data = response.json()
    
    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="GitHub authentication failed")
    
    # Get user info from GitHub
    github_token = token_data["access_token"]
    github_user = requests.get(
        "https://api.github.com/user", 
        headers={"Authorization": f"token {github_token}"}
    ).json()
    
    # Get email if not public in profile
    if not github_user.get("email"):
        emails = requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"token {github_token}"}
        ).json()
        primary_email = next((e["email"] for e in emails if e.get("primary")), None)
        github_user["email"] = primary_email
    
    # Check if user exists
    user = db.query(User).filter(User.email == github_user["email"]).first()
    
    if not user:
        # Create new user
        new_user = User(
            email=github_user["email"],
            username=github_user.get("login") or github_user["email"].split("@")[0],
            hashed_password="GITHUB_AUTH",  # Set a placeholder since GitHub auth doesn't use password
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
    
    # Create JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Return token
    return {"access_token": access_token, "token_type": "bearer"}

# Other auth routes...
