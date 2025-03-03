from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from pydantic import BaseModel
from datetime import datetime

# These would need to be implemented in their respective files
from dependencies.auth import get_current_user
from services.file_processor import process_file_with_rope
from services.vector_optimizer import optimize_vectors
from db.weaviate_client import store_vectors_in_weaviate
from db.redis_client import update_processing_status, get_processing_status
from database.db import get_db
from models import Knowledge, User, KnowledgeBase
from schemas import KnowledgeResponse, KnowledgeBaseResponse, KnowledgeCreate

# Define response models
class FileUploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    created_at: datetime

class ProcessingStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    completed_at: Optional[datetime] = None

# Define additional models
class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    filename: Optional[str] = None
    content_type: Optional[str] = None

class SearchResult(BaseModel):
    content: str
    filename: str
    content_type: Optional[str] = None
    page: Optional[int] = None
    processed_at: Optional[datetime] = None

# Set up the router
router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}}
)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload knowledge files (PDF, Excel, JSON, TXT) for processing and indexing
    """
    # Validate file type
    allowed_types = ["application/pdf", "application/json", "text/plain", 
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel"]
    
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, 
                           detail="File type not supported. Please upload PDF, Excel, JSON, or TXT files.")
    
    # Generate job ID for tracking
    job_id = str(uuid.uuid4())
    
    # Save file temporarily
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = f"{temp_dir}/{job_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Queue background processing task
    background_tasks.add_task(
        process_and_store_file,
        file_path=file_path,
        file_name=file.filename,
        content_type=file.content_type,
        user_id=current_user["id"],
        job_id=job_id
    )
    
    # Create initial status in Redis
    update_processing_status(job_id, {
        "status": "processing",
        "progress": 0.0,
        "message": "File received, starting processing",
        "filename": file.filename,
        "user_id": current_user["id"]
    })
    
    return FileUploadResponse(
        job_id=job_id,
        filename=file.filename,
        status="processing",
        created_at=datetime.now()
    )

@router.get("/status/{job_id}", response_model=ProcessingStatus)
async def check_processing_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check the status of a file processing job
    """
    status_data = get_processing_status(job_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Processing job not found")
    
    # Verify the job belongs to the current user
    if status_data.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    
    return ProcessingStatus(
        job_id=job_id,
        status=status_data.get("status", "unknown"),
        progress=status_data.get("progress", 0.0),
        message=status_data.get("message"),
        completed_at=status_data.get("completed_at")
    )

async def process_and_store_file(file_path: str, file_name: str, content_type: str, user_id: str, job_id: str):
    """
    Background task to process files using ROPE Chunking and vector optimization
    """
    try:
        # Update status
        update_processing_status(job_id, {
            "status": "processing", 
            "progress": 0.1,
            "message": "Starting ROPE chunking process"
        })
        
        # Step 1: Process the file using ROPE Chunking
        chunks = process_file_with_rope(file_path, content_type)
        
        update_processing_status(job_id, {
            "status": "processing", 
            "progress": 0.4,
            "message": "File chunking complete, optimizing vectors"
        })
        
        # Step 2: Optimize vectors (batch processing and compression)
        optimized_vectors = optimize_vectors(chunks)
        
        update_processing_status(job_id, {
            "status": "processing", 
            "progress": 0.7,
            "message": "Vector optimization complete, storing in databases"
        })
        
        # Step 3: Store in Weaviate
        store_vectors_in_weaviate(
            vectors=optimized_vectors,
            metadata={
                "filename": file_name,
                "user_id": user_id,
                "job_id": job_id,
                "content_type": content_type,
                "processed_at": datetime.now().isoformat()
            }
        )
        
        # Step 4: Final status update
        update_processing_status(job_id, {
            "status": "completed", 
            "progress": 1.0,
            "message": "Processing completed successfully",
            "completed_at": datetime.now()
        })
        
    except Exception as e:
        # Update status with error information
        update_processing_status(job_id, {
            "status": "failed",
            "progress": 0.0,
            "message": f"Processing failed: {str(e)}"
        })
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

# Add search endpoint
@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    search_query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    Search through knowledge base using hybrid search (vector + keywords)
    """
    # Get results from Weaviate
    from db.weaviate_client import hybrid_search
    
    filters = {
        "filename": search_query.filename,
        "content_type": search_query.content_type
    }
    
    results = hybrid_search(
        query=search_query.query,
        user_id=current_user["id"],
        limit=search_query.limit,
        filters={k: v for k, v in filters.items() if v is not None}
    )
    
    return results

@router.get("/jobs", response_model=List[FileUploadResponse])
async def list_processing_jobs(
    current_user: dict = Depends(get_current_user)
):
    """
    List all file processing jobs for the current user
    """
    from db.redis_client import list_user_jobs
    
    jobs = list_user_jobs(current_user["id"])
    
    return [
        FileUploadResponse(
            job_id=job["job_id"],
            filename=job["filename"],
            status=job["status"],
            created_at=job.get("created_at") or datetime.now()
        ) for job in jobs
    ]

@router.get("/by_user/{user_id}", response_model=List[KnowledgeResponse])
async def get_knowledge_by_user(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los conocimientos de un usuario específico.
    Solo el propio usuario o un administrador pueden acceder.
    """
    # Verificar permisos
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para ver estos conocimientos"
        )
    
    knowledge_items = db.query(Knowledge).filter(
        Knowledge.user_id == user_id
    ).offset(offset).limit(limit).all()
    
    return knowledge_items

@router.get("/bases/by_user/{user_id}", response_model=List[KnowledgeBaseResponse])
async def get_knowledge_bases_by_user(
    user_id: int,
    include_system: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las bases de conocimiento de un usuario específico.
    Con opción de incluir las bases del sistema.
    """
    # Verificar permisos
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para ver estas bases de conocimiento"
        )
    
    # Crear consulta base
    query = db.query(KnowledgeBase)
    
    if include_system:
        # Incluir bases del usuario y bases del sistema
        query = query.filter(
            (KnowledgeBase.user_id == user_id) | 
            (KnowledgeBase.is_system_base == True)
        )
    else:
        # Solo bases del usuario
        query = query.filter(KnowledgeBase.user_id == user_id)
    
    knowledge_bases = query.all()
    return knowledge_bases

@router.get("/bases/{base_id}/knowledge", response_model=List[KnowledgeResponse])
async def get_knowledge_by_base(
    base_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todo el conocimiento asociado a una base específica.
    Verificando permisos de acceso.
    """
    # Primero obtener la base para verificar permisos
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == base_id).first()
    
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    # Verificar permisos
    if (knowledge_base.user_id != current_user.id and 
        not knowledge_base.is_system_base and 
        not current_user.is_superuser):
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para acceder a esta base de conocimiento"
        )
    
    # Obtener los conocimientos asociados a la base
    knowledge_items = db.query(Knowledge).filter(
        Knowledge.base_id == base_id
    ).all()
    
    return knowledge_items

@router.post("/user/{user_id}/item", response_model=KnowledgeResponse)
async def add_knowledge_to_user(
    user_id: int,
    knowledge_item: KnowledgeCreate,
    base_id: Optional[int] = Query(None, description="ID de la base de conocimiento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Añade un nuevo elemento de conocimiento para un usuario específico.
    Puede asociarse opcionalmente a una base de conocimiento existente.
    """
    # Verificar permisos
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para añadir conocimiento a este usuario"
        )
    
    # Verificar si la base de conocimiento existe (si se proporcionó)
    if base_id:
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == base_id,
            (KnowledgeBase.user_id == user_id) | (KnowledgeBase.is_system_base == True)
        ).first()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Base de conocimiento no encontrada o no pertenece al usuario"
            )
    
    # Verificar si ya existe un conocimiento con el mismo nombre
    existing = db.query(Knowledge).filter(
        Knowledge.user_id == user_id,
        Knowledge.name == knowledge_item.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un conocimiento con este nombre para este usuario"
        )
    
    # Crear hash de contenido para verificar duplicados
    import hashlib
    content_string = str(knowledge_item.vector_ids or {})
    content_hash = hashlib.md5(content_string.encode()).hexdigest()
    
    # Crear el nuevo item de conocimiento
    new_knowledge = Knowledge(
        user_id=user_id,
        name=knowledge_item.name,
        vector_ids=knowledge_item.vector_ids or {},
        content_hash=content_hash,
        base_id=base_id
    )
    
    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)
    
    return new_knowledge

# Endpoint para recursos del usuario actual
@router.post("/knowledge", response_model=KnowledgeResponse)
async def add_my_knowledge(
    knowledge_item: KnowledgeCreate,
    base_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Añade conocimiento al usuario autenticado"""
    # Usar el ID del token directamente
    user_id = current_user.id
    # Verificar si la base de conocimiento existe (si se proporcionó)
    if base_id:
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == base_id,
            (KnowledgeBase.user_id == user_id) | (KnowledgeBase.is_system_base == True)
        ).first()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Base de conocimiento no encontrada o no pertenece al usuario"
            )
    
    # Verificar si ya existe un conocimiento con el mismo nombre
    existing = db.query(Knowledge).filter(
        Knowledge.user_id == user_id,
        Knowledge.name == knowledge_item.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un conocimiento con este nombre para este usuario"
        )
    
    # Crear hash de contenido para verificar duplicados
    import hashlib
    content_string = str(knowledge_item.vector_ids or {})
    content_hash = hashlib.md5(content_string.encode()).hexdigest()
    
    # Crear el nuevo item de conocimiento
    new_knowledge = Knowledge(
        user_id=user_id,
        name=knowledge_item.name,
        vector_ids=knowledge_item.vector_ids or {},
        content_hash=content_hash,
        base_id=base_id
    )
    
    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)
    
    return new_knowledge

# Endpoint para recursos de cualquier usuario (admin)
@router.post("/users/{user_id}/knowledge", response_model=KnowledgeResponse)
async def add_user_knowledge(
    user_id: int,
    knowledge_item: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permite a administradores gestionar conocimiento de otros usuarios"""
    # Verificar que sea admin o el mismo usuario
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Operación no permitida")
    # Verificar si la base de conocimiento existe (si se proporcionó)
    if base_id:
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == base_id,
            (KnowledgeBase.user_id == user_id) | (KnowledgeBase.is_system_base == True)
        ).first()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Base de conocimiento no encontrada o no pertenece al usuario"
            )
    
    # Verificar si ya existe un conocimiento con el mismo nombre
    existing = db.query(Knowledge).filter(
        Knowledge.user_id == user_id,
        Knowledge.name == knowledge_item.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un conocimiento con este nombre para este usuario"
        )
    
    # Crear hash de contenido para verificar duplicados
    import hashlib
    content_string = str(knowledge_item.vector_ids or {})
    content_hash = hashlib.md5(content_string.encode()).hexdigest()
    
    # Crear el nuevo item de conocimiento
    new_knowledge = Knowledge(
        user_id=user_id,
        name=knowledge_item.name,
        vector_ids=knowledge_item.vector_ids or {},
        content_hash=content_hash,
        base_id=base_id
    )
    
    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)
    
    return new_knowledge

