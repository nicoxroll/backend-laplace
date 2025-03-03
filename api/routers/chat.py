from fastapi import APIRouter, Depends, HTTPException
from models import Chat, ChatMessage
from database.db import get_db
from db.weaviate_client import hybrid_search
from db.redis_client import cache_chunks
from utils.ollama_client import generate_response
import uuid
from typing import List
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/chats", response_model=Chat)
async def create_chat(request: dict, db: Session = Depends(get_db)):
    chat = Chat(
        id=uuid.uuid4(),
        user_id=request.get("user_id"),
        title=request.get("title", "New Chat"),
        created_at=datetime.now()
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat

@router.post("/chats/{chat_id}/messages", response_model=ChatMessage)
async def send_message(chat_id: int, request: dict, db: Session = Depends(get_db)):
    # Asegúrate de que chat_id sea del tipo correcto
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    cache_key = f"chat:{chat_id}:message:{request['content']}"
    
    if cached := await cache_chunks.get(cache_key):
        return cached
    
    # Search context from Weaviate
    context = await hybrid_search(request)
    
    # Generate AI response
    ai_response = await generate_response(context, request)
    
    # Store user message
    user_message = ChatMessage(
        id=uuid.uuid4(),
        chat_id=chat_id,
        role="user",
        content=request["content"],
        created_at=datetime.now()
    )
    
    # Store AI response
    ai_message = ChatMessage(
        id=uuid.uuid4(),
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        created_at=datetime.now()
    )
    
    db.add(user_message)
    db.add(ai_message)
    await db.commit()
    
    # Cache the response
    await cache_chunks.set(cache_key, ai_message, 3600)
    
    return ai_message

@router.get("/chats", response_model=List[Chat])
async def get_chats(user_id: str, db: Session = Depends(get_db)):
    chats = await db.query(Chat).filter(Chat.user_id == user_id).all()
    return chats

@router.get("/chats/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str, db: Session = Depends(get_db)):
    chat = await db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.get("/chats/{chat_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(chat_id: str, db: Session = Depends(get_db)):
    messages = await db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
    return messages

@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    chat = await db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    await db.delete(chat)
    await db.commit()
    
    return {"message": "Chat deleted successfully"}
