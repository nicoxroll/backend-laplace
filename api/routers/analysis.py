from fastapi import APIRouter, Depends, HTTPException
from models import AnalysisResult
from database.db import get_db
from utils.weaviate_client import search_hybrid
from utils.redis_client import cache
from utils.ollama_client import generate_response
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

router = APIRouter()

@router.post("/analyze")
async def analyze_endpoint(request: dict, db: Session = Depends(get_db)):
    cache_key = f"analysis:{request['query']}"
    
    if cached := await cache.get(cache_key):
        return cached
    
    try:
        # Lógica de análisis usando Weaviate y Ollama
        context = await search_hybrid(request)
        response = await generate_response(context, request)
        
        # Guardar en PostgreSQL
        analysis = AnalysisResult(
            id=uuid.uuid4(),
            query=request.get("query"),
            response=response,
            context_used=context,
            created_at=datetime.now()
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        
        # Cachear respuesta
        await cache.set(cache_key, response, 3600)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/analyses", response_model=List[AnalysisResult])
async def get_analyses(user_id: str = None, db: Session = Depends(get_db)):
    query = db.query(AnalysisResult)
    if user_id:
        query = query.filter(AnalysisResult.user_id == user_id)
    
    analyses = await query.order_by(AnalysisResult.created_at.desc()).all()
    return analyses

@router.get("/analyses/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = await db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis