from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.db import get_db
from models import Chat, ChatMessage
from schemas import ChatCreate, ChatResponse

router = APIRouter()

@router.post("/", response_model=ChatResponse)
def create_chat(chat: ChatCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # Correct usage without await for synchronous SQLAlchemy
    db_chat = Chat(
        user_id=user_id,
        agent_id=chat.agent_id,
        title=chat.title
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # Correct usage without await for synchronous SQLAlchemy
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
