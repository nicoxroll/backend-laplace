import os
import json
import pandas as pd
import brotli
import asyncio
import numpy as np
from typing import List, Dict, Any, AsyncGenerator
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    JSONLoader
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ROPEChunker:
    def __init__(self):
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"}
        )
    
    def chunk_text(self, text: str, chunk_size=1000, overlap=200) -> List[Dict[str, Any]]:
        """Apply ROPE chunking to a text"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=overlap,
        )
        chunks = text_splitter.create_documents([text])
        
        embedded_chunks = []
        for chunk in chunks:
            embedding = self.embedding_model.embed_query(chunk.page_content)
            embedded_chunks.append({
                "content": chunk.page_content,
                "embedding": embedding,
                "metadata": chunk.metadata
            })
        
        return embedded_chunks
    
    def chunk_code_by_functions(self, code: str, overlap=100) -> List[Dict[str, Any]]:
        """Split code by function/class definitions with context"""
        # This is a simplified approach - a real implementation would use AST parsing
        import re
        pattern = r"(def\s+\w+|class\s+\w+)"
        splits = re.split(pattern, code)
        
        chunks = []
        for i in range(1, len(splits), 2):
            # Combine function/class keyword with its implementation
            if i+1 < len(splits):
                func_chunk = splits[i] + splits[i+1]
            else:
                func_chunk = splits[i]
                
            # Add some context from previous chunk for overlap
            if i >= 3:
                context = splits[i-2][-overlap:] + splits[i-1]
                func_chunk = context + func_chunk
                
            chunks.append({"content": func_chunk, "metadata": {"type": "code_function"}})
            
        # Process chunks normally after splitting
        return self.chunk_text("\n".join([c["content"] for c in chunks]))
    
    def chunk_by_headings(self, markdown: str, chunk_size=1500) -> List[Dict[str, Any]]:
        """Split markdown by headings"""
        import re
        pattern = r"(#{1,6}\s+.+)"
        sections = re.split(pattern, markdown)
        
        chunks = []
        current_section = ""
        current_heading = ""
        
        for i, section in enumerate(sections):
            # If this is a heading
            if re.match(pattern, section):
                # Store previous section if it exists
                if current_section:
                    chunks.append({
                        "content": current_section,
                        "metadata": {"heading": current_heading, "type": "markdown_section"}
                    })
                current_heading = section
                current_section = section
            else:
                current_section += section
                
                # If section gets too large, split it
                if len(current_section) > chunk_size:
                    chunks.append({
                        "content": current_section,
                        "metadata": {"heading": current_heading, "type": "markdown_section"}
                    })
                    current_section = ""
        
        # Add the last section
        if current_section:
            chunks.append({
                "content": current_section,
                "metadata": {"heading": current_heading, "type": "markdown_section"}
            })
            
        # Process chunks normally after splitting
        return self.chunk_text("\n".join([c["content"] for c in chunks]))

def adaptive_chunking(file: bytes, content_type: str) -> List[Dict[str, Any]]:
    """
    Intelligently chunk content based on its type
    """
    chunker = ROPEChunker()
    
    # Detect language/format for specialized chunking
    if content_type.endswith('/python'):
        return chunker.chunk_code_by_functions(file.decode('utf-8'))
    elif content_type == "text/markdown":
        return chunker.chunk_by_headings(file.decode('utf-8'))
    elif content_type == "application/pdf":
        # Process PDFs page by page with specialized chunking
        with open("temp.pdf", "wb") as f:
            f.write(file)
        
        loader = PyPDFLoader("temp.pdf")
        pages = loader.load()
        chunks = []
        
        for page in pages:
            page_chunks = chunker.chunk_text(page.page_content)
            for chunk in page_chunks:
                chunk["metadata"].update({"page": page.metadata.get("page", 0)})
            chunks.extend(page_chunks)
        
        os.remove("temp.pdf")
        return chunks
    else:
        # Default chunking for other content types
        text = file.decode('utf-8', errors='ignore')
        return chunker.chunk_text(text)

async def process_upload(file_stream: AsyncGenerator, user_id: str, filename: str, content_type: str):
    """
    Process file as it's being uploaded without saving to disk
    """
    import torch
    from db.weaviate_client import store_vectors_in_weaviate
    from db.redis_client import update_processing_status, cache_chunks
    
    # Generate job ID for tracking
    job_id = str(uuid.uuid4())
    
    try:
        # Initialize processing status
        update_processing_status(job_id, {
            "status": "processing", 
            "progress": 0.1,
            "message": "Starting file processing",
            "filename": filename,
            "user_id": user_id
        })
        
        # Process file in streaming chunks
        all_chunks = []
        buffer = b''
        
        # Stream process the file
        async for chunk in file_stream:
            buffer += chunk
            
            # Process in reasonable sized chunks (1MB)
            if len(buffer) >= 1024 * 1024:  
                # Detect content type for specialized handling
                file_chunks = adaptive_chunking(buffer, content_type)
                all_chunks.extend(file_chunks)
                buffer = b''
                
                # Update progress
                progress = min(0.1 + 0.5 * (len(all_chunks) / 500), 0.6)  # Estimate progress
                update_processing_status(job_id, {
                    "status": "processing", 
                    "progress": progress,
                    "message": f"Processed {len(all_chunks)} chunks"
                })
                
                # Batch upload if we have enough chunks
                if len(all_chunks) >= 100:
                    await parallel_vector_upload(
                        all_chunks[:100], 
                        user_id, 
                        filename, 
                        content_type, 
                        job_id
                    )
                    all_chunks = all_chunks[100:]
        
        # Process any remaining buffer content
        if buffer:
            file_chunks = adaptive_chunking(buffer, content_type)
            all_chunks.extend(file_chunks)
        
        # Upload any remaining chunks
        if all_chunks:
            await parallel_vector_upload(
                all_chunks, 
                user_id, 
                filename, 
                content_type, 
                job_id
            )
            
        # Cache processed chunks for faster retrieval
        cache_chunks(user_id, job_id, all_chunks)
        
        # Update final status
        update_processing_status(job_id, {
            "status": "completed", 
            "progress": 1.0,
            "message": "Processing completed successfully",
            "completed_at": datetime.now()
        })
        
        return job_id
        
    except Exception as e:
        # Update status with error information
        update_processing_status(job_id, {
            "status": "failed",
            "progress": 0.0,
            "message": f"Processing failed: {str(e)}"
        })
        raise

async def parallel_vector_upload(chunks: list, user_id: str, filename: str, content_type: str, job_id: str):
    """Upload vectors in parallel with compression"""
    from services.vector_optimizer import optimize_vectors
    from db.weaviate_client import store_vectors_in_weaviate
    
    # Optimize vectors before upload
    optimized = optimize_vectors(chunks)
    
    # Compress content for larger chunks
    for chunk in optimized:
        if len(chunk["content"]) > 1024:
            chunk["content_compressed"] = brotli.compress(chunk["content"].encode())
            chunk["compression"] = "brotli"
            # Keep a preview of the content for debugging
            chunk["content_preview"] = chunk["content"][:100] + "..."
        
    # Create tasks for parallel processing
    tasks = []
    batch_size = 32  # Adjust based on system capabilities
    
    for i in range(0, len(optimized), batch_size):
        batch = optimized[i:i+batch_size]
        tasks.append(
            asyncio.create_task(
                store_vectors_in_weaviate(
                    vectors=batch,
                    metadata={
                        "user_id": user_id,
                        "filename": filename,
                        "content_type": content_type,
                        "job_id": job_id,
                        "processed_at": datetime.now().isoformat()
                    }
                )
            )
        )
    
    
    # Wait for all uploads to complete
    await asyncio.gather(*tasks)

def process_file_with_rope(file_path: str, content_type: str) -> List[Dict[str, Any]]:
    """
    Process a file using ROPE Chunking strategy based on content type.
    
    Args:
        file_path: Path to the file to process
        content_type: MIME type of the file
        
    Returns:
        List of chunks with embeddings
    """
    import os
    import torch
    
    # Instanciar el chunker
    chunker = ROPEChunker()
    
    # Leer el contenido del archivo
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # Determinar estrategia de procesamiento basada en content_type
    if content_type.startswith('text/plain'):
        # Texto plano
        text = file_content.decode('utf-8', errors='ignore')
        return chunker.chunk_text(text)
        
    elif 'python' in content_type or file_path.endswith('.py'):
        # Código Python
        code = file_content.decode('utf-8', errors='ignore')
        return chunker.chunk_code_by_functions(code)
        
    elif 'markdown' in content_type or file_path.endswith(('.md', '.markdown')):
        # Markdown
        markdown = file_content.decode('utf-8', errors='ignore')
        return chunker.chunk_by_headings(markdown)
        
    elif 'pdf' in content_type or file_path.endswith('.pdf'):
        # PDF - usar PyPDFLoader si es posible
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        chunks = []
        for doc in docs:
            embedding = chunker.embedding_model.embed_query(doc.page_content)
            chunks.append({
                "content": doc.page_content,
                "embedding": embedding,
                "metadata": doc.metadata
            })
        return chunks
    
    elif 'json' in content_type or file_path.endswith('.json'):
        # JSON
        import json
        try:
            data = json.loads(file_content.decode('utf-8'))
            text = json.dumps(data, indent=2)
            return chunker.chunk_text(text)
        except:
            # Si falla el parsing, tratar como texto
            return chunker.chunk_text(file_content.decode('utf-8', errors='ignore'))
    
    else:
        # Para otros tipos de archivo, usar chunking adaptativo
        return adaptive_chunking(file_content, content_type)
