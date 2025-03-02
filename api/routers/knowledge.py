from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
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

