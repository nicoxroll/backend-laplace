from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import uuid
import hashlib
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

# Importaciones internas
from dependencies.auth import get_current_user
from services.file_processor import process_file_with_rope
from services.vector_optimizer import optimize_vectors
from db.weaviate_client import store_vectors_in_weaviate, hybrid_search
from db.redis_client import update_processing_status, get_processing_status, list_user_jobs
from database.db import get_db
from models import Knowledge, User, KnowledgeBase
from schemas import (KnowledgeResponse, KnowledgeBaseResponse, KnowledgeCreate,
                     KnowledgeBaseCreate, KnowledgeBaseUpdate)

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

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    filename: Optional[str] = None
    created_at: datetime
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
    tags=["knowledge"],
    responses={404: {"description": "Not found"}}
)

# === KNOWLEDGE ITEMS ENDPOINTS ===

@router.get("/items", response_model=List[KnowledgeResponse])
async def get_all_knowledge(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los elementos de conocimiento a los que tiene acceso el usuario actual:
    - Sus propios elementos
    - Elementos del sistema (si corresponde)
    """
    # Obtener usuario sistema
    system_user = db.query(User).filter(User.is_system_user == True).first()
    system_id = system_user.id if system_user else None
    
    # Construir consulta para obtener conocimiento del usuario + sistema
    query = db.query(Knowledge).filter(
        (Knowledge.user_id == current_user.id) |
        (Knowledge.user_id == system_id)
    )
    
    knowledge_items = query.offset(offset).limit(limit).all()
    return knowledge_items

@router.get("/items/user/{user_id}", response_model=List[KnowledgeResponse])
async def get_user_knowledge_items(
    user_id: int,
    include_system: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los conocimientos de un usuario específico.
    """
    # Verificar permisos
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    # Consultar conocimientos
    query = db.query(Knowledge).filter(Knowledge.user_id == user_id)
    
    # Incluir conocimientos del sistema si se solicita
    if include_system:
        system_user = db.query(User).filter(User.is_system_user == True).first()
        if (system_user):
            query = query.union_all(
                db.query(Knowledge).filter(Knowledge.user_id == system_user.id)
            )
    
    knowledge_items = query.all()
    return knowledge_items

@router.post("/items", response_model=KnowledgeResponse)
async def add_my_knowledge_item(
    knowledge_item: KnowledgeCreate,
    base_id: Optional[int] = Query(None, description="ID de la base de conocimiento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Añade conocimiento al usuario autenticado"""
    # Verificar si existe la base de conocimiento si se proporciona
    if base_id is not None:
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == base_id,
            ((KnowledgeBase.user_id == current_user.id) | (KnowledgeBase.is_system_base == True))
        ).first()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Base de conocimiento no encontrada o no tienes acceso"
            )
    
    # Verificar si ya existe un conocimiento con el mismo nombre
    existing = db.query(Knowledge).filter(
        Knowledge.user_id == current_user.id,
        Knowledge.name == knowledge_item.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un conocimiento con este nombre"
        )
    
    # Calcular hash del contenido o generar uno único si no hay contenido
    content_hash = None
    if knowledge_item.content:
        content_hash = hashlib.md5(knowledge_item.content.encode('utf-8')).hexdigest()
    else:
        # Generar hash único basado en nombre y timestamp
        import time
        content_hash = hashlib.md5(f"{current_user.id}_{knowledge_item.name}_{time.time()}".encode('utf-8')).hexdigest()
    
    # Crear nueva estructura vector_ids con el contenido
    vector_ids = {}
    if knowledge_item.content:
        vector_ids["content"] = knowledge_item.content
    
    if knowledge_item.description:
        vector_ids["description"] = knowledge_item.description
    
    new_knowledge = Knowledge(
        user_id=current_user.id,
        name=knowledge_item.name,
        description=knowledge_item.description,
        content_hash=content_hash,
        base_id=base_id,
        vector_ids=vector_ids
    )
    
    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)
    
    return new_knowledge

@router.post("/items/user/{user_id}", response_model=KnowledgeResponse)
async def add_knowledge_to_user(
    user_id: int,
    knowledge_item: KnowledgeCreate,
    base_id: Optional[int] = Query(None, description="ID de la base de conocimiento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Añade un elemento de conocimiento para un usuario específico.
    Requiere permisos de administrador o ser el propio usuario.
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

@router.put("/items/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge_item(
    knowledge_id: int,
    knowledge_update: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un elemento de conocimiento.
    El usuario debe ser propietario o administrador.
    """
    # Obtener el item de conocimiento existente
    knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Elemento de conocimiento no encontrado")
    
    # Verificar permisos
    if knowledge.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para modificar este elemento de conocimiento"
        )
    
    # Verificar nombre único si se está cambiando
    if knowledge_update.name != knowledge.name:
        existing = db.query(Knowledge).filter(
            Knowledge.user_id == knowledge.user_id,
            Knowledge.name == knowledge_update.name,
            Knowledge.id != knowledge_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Ya existe otro elemento con este nombre"
            )
    
    # Actualizar los campos
    knowledge.name = knowledge_update.name
    knowledge.description = knowledge_update.description
    
    # Si se proporciona contenido nuevo, actualizar el hash y los vector_ids
    if knowledge_update.content:
        # Calcular nuevo hash
        content_hash = hashlib.md5(knowledge_update.content.encode('utf-8')).hexdigest()
        knowledge.content_hash = content_hash
        
        # Inicializar o actualizar vector_ids
        if not knowledge.vector_ids:
            knowledge.vector_ids = {}
        
        knowledge.vector_ids["content"] = knowledge_update.content
        
        # Si hay descripción, también la incluimos
        if knowledge_update.description:
            knowledge.vector_ids["description"] = knowledge_update.description
    else:
        # Solo actualizar la descripción en vector_ids si existe y se proporciona nueva
        if knowledge.vector_ids and knowledge_update.description:
            knowledge.vector_ids["description"] = knowledge_update.description
    
    db.commit()
    db.refresh(knowledge)
    
    return knowledge

@router.delete("/items/{knowledge_id}", status_code=204)
async def delete_knowledge_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un elemento de conocimiento.
    El usuario debe ser propietario o administrador.
    """
    knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Elemento de conocimiento no encontrado")
    
    # Verificar permisos
    if knowledge.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar este elemento de conocimiento"
        )
    
    db.delete(knowledge)
    db.commit()
    
    return None

# === KNOWLEDGE BASES ENDPOINTS ===

@router.get("/bases", response_model=List[KnowledgeBaseResponse])
async def get_knowledge_bases(
    include_system: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las bases de conocimiento del usuario actual.
    Opcionalmente incluye las bases del sistema.
    """
    # Crear consulta base
    query = db.query(KnowledgeBase)
    
    if include_system:
        # Incluir bases del usuario y bases del sistema
        query = query.filter(
            (KnowledgeBase.user_id == current_user.id) | 
            (KnowledgeBase.is_system_base == True)
        )
    else:
        # Solo bases del usuario
        query = query.filter(KnowledgeBase.user_id == current_user.id)
    
    knowledge_bases = query.all()
    return knowledge_bases

@router.get("/bases/user/{user_id}", response_model=List[KnowledgeBaseResponse])
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

@router.get("/bases/{base_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información sobre una base de conocimiento específica
    """
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
    
    return knowledge_base

@router.get("/bases/{base_id}/items", response_model=List[KnowledgeResponse])
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

@router.post("/bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva base de conocimiento para el usuario actual
    """
    # Verificar si ya existe una base de conocimiento con el mismo nombre para este usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == current_user.id,
        KnowledgeBase.name == knowledge_base.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una base de conocimiento con este nombre")
    
    new_kb = KnowledgeBase(
        user_id=current_user.id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        vector_config=knowledge_base.vector_config or {}
    )
    
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    return new_kb

@router.post("/bases/user/{user_id}", response_model=KnowledgeBaseResponse)
async def create_user_knowledge_base(
    user_id: int,
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva base de conocimiento para un usuario específico
    """
    # Verificar permisos (solo el mismo usuario o superusuario)
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para crear bases de conocimiento para este usuario")
    
    # Verificar si ya existe una base de conocimiento con el mismo nombre para este usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user_id,
        KnowledgeBase.name == knowledge_base.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una base de conocimiento con este nombre")
    
    new_kb = KnowledgeBase(
        user_id=user_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        vector_config=knowledge_base.vector_config or {}
    )
    
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    return new_kb

@router.put("/bases/{base_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    base_id: int,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza una base de conocimiento existente
    """
    # Verificar si la base de conocimiento existe y pertenece al usuario
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == base_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    # Verificar permisos
    if existing.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta base de conocimiento")
    
    # Actualizar los campos proporcionados
    if knowledge_base.name is not None:
        # Verificar si el nuevo nombre ya existe para otro conocimiento del usuario
        name_exists = db.query(KnowledgeBase).filter(
            KnowledgeBase.user_id == existing.user_id,
            KnowledgeBase.name == knowledge_base.name,
            KnowledgeBase.id != base_id
        ).first()
        
        if name_exists:
            raise HTTPException(status_code=409, detail="Ya existe otra base de conocimiento con este nombre")
        
        existing.name = knowledge_base.name
    
    if knowledge_base.description is not None:
        existing.description = knowledge_base.description
    
    if knowledge_base.vector_config is not None:
        existing.vector_config = knowledge_base.vector_config
    
    db.commit()
    db.refresh(existing)
    
    return existing

@router.delete("/bases/{base_id}", status_code=204)
async def delete_knowledge_base(
    base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina una base de conocimiento
    """
    # Verificar si la base de conocimiento existe
    existing = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == base_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Base de conocimiento no encontrada")
    
    # Verificar permisos
    if existing.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta base de conocimiento")
    
    # Eliminar la base de conocimiento
    db.delete(existing)
    db.commit()
    
    return None

# === FILE UPLOAD ENDPOINTS ===

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Sube un archivo para ser procesado e indexado"""
    job_id = str(uuid.uuid4())
    
    # Crear directorio temporal si no existe
    os.makedirs("./temp", exist_ok=True)
    
    # Guardar archivo en directorio temporal
    file_path = f"./temp/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Programar tarea en segundo plano
    background_tasks.add_task(
        process_and_store_file,
        file_path=file_path,
        file_name=file.filename,
        content_type=file.content_type,
        user_id=current_user.id,
        job_id=job_id
    )
    
    # Crear estado inicial en Redis
    update_processing_status(job_id, {
        "status": "processing",
        "progress": 0.0,
        "message": "Archivo recibido, comenzando procesamiento",
        "filename": file.filename,
        "user_id": current_user.id
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
    current_user: User = Depends(get_current_user)
):
    """
    Check the processing status of an uploaded file
    """
    status = get_processing_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Verify the job belongs to the user
    if str(status.get("user_id")) != str(current_user.id) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
        
    return ProcessingStatus(
        job_id=job_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0.0),
        message=status.get("message"),
        completed_at=status.get("completed_at")
    )

@router.get("/job/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obtiene el estado actual de un trabajo de procesamiento"""
    status = get_processing_status(job_id)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Trabajo con ID {job_id} no encontrado"
        )
    
    # Verificar que el trabajo pertenece al usuario actual
    if str(status.get("user_id")) != str(current_user.id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver este trabajo"
        )
    
    return JobStatusResponse(
        job_id=job_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0.0),
        message=status.get("message", ""),
        filename=status.get("filename", ""),
        created_at=status.get("created_at", datetime.now()),
        completed_at=status.get("completed_at")
    )

@router.get("/jobs", response_model=List[FileUploadResponse])
async def list_processing_jobs(
    current_user: User = Depends(get_current_user)
):
    """
    List all file processing jobs for the current user
    """
    jobs = list_user_jobs(current_user.id)
    
    return [
        FileUploadResponse(
            job_id=job["job_id"],
            filename=job["filename"],
            status=job["status"],
            created_at=job.get("created_at") or datetime.now()
        ) for job in jobs
    ]

@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_user)
):
    """
    Search through knowledge base using hybrid search (vector + keywords)
    """
    filters = {
        "filename": search_query.filename,
        "content_type": search_query.content_type
    }
    
    results = hybrid_search(
        query=search_query.query,
        user_id=current_user.id,
        limit=search_query.limit,
        filters={k: v for k, v in filters.items() if v is not None}
    )
    
    return results

# Helper function for file processing
async def process_and_store_file(file_path: str, file_name: str, content_type: str, user_id: str, job_id: str):
    try:
        # Actualizar progreso
        update_processing_status(job_id, {
            "status": "processing",
            "progress": 0.2,
            "message": "Procesando contenido del archivo"
        })
        
        # Procesar el archivo usando ROPE
        chunks = process_file_with_rope(file_path, content_type)
        
        update_processing_status(job_id, {
            "status": "processing",
            "progress": 0.5,
            "message": "Optimizando vectores"
        })
        
        # Optimizar vectores para almacenamiento
        vectors = optimize_vectors(chunks)
        
        update_processing_status(job_id, {
            "status": "processing",
            "progress": 0.8,
            "message": "Almacenando en base de datos vectorial"
        })
        
        # Almacenar en Weaviate
        store_vectors_in_weaviate(vectors, {
            "user_id": user_id,
            "filename": file_name,
            "job_id": job_id,
            "content_type": content_type,
            "processed_at": datetime.now().isoformat()
        })
        
        # Actualizar status como completado
        update_processing_status(job_id, {
            "status": "completed",
            "progress": 1.0,
            "message": "Procesamiento completado con éxito",
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        # Log y actualizar estado en caso de error
        logger.error(f"Error processing file {file_name}: {str(e)}")
        update_processing_status(job_id, {
            "status": "failed",
            "message": f"Error en procesamiento: {str(e)}"
        })
        
    finally:
        # Eliminar archivo temporal
        try:
            os.remove(file_path)
        except:
            pass

@router.get("/debug-model", response_model=dict)
async def debug_knowledge_model():
    """Endpoint para depurar la estructura del modelo Knowledge"""
    from inspect import getmembers
    from models import Knowledge
    
    # Obtener todos los atributos del modelo
    model_info = {}
    
    # Examinar las columnas de SQLAlchemy
    if hasattr(Knowledge, "__table__"):
        model_info["columns"] = [column.name for column in Knowledge.__table__.columns]
        
    # Examinar los campos del constructor
    import inspect
    constructor_signature = inspect.signature(Knowledge.__init__)
    model_info["constructor_params"] = list(constructor_signature.parameters.keys())
    
    # Obtener algunos metadatos adicionales
    model_info["model_name"] = Knowledge.__name__
    
    return model_info

