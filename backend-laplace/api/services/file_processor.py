import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any
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
            model_kwargs={"device": "cpu"}
        )
    
    def chunk_text(self, text: str, chunk_size=1000, overlap=200) -> List[Dict[str, Any]]:
        """
        Apply ROPE (Recursive Overlap Partition Embeddings) chunking to a text
        """
        # First, split the text into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )
        chunks = text_splitter.create_documents([text])
        
        # Get embeddings for chunks
        embedded_chunks = []
        for chunk in chunks:
            embedding = self.embedding_model.embed_query(chunk.page_content)
            embedded_chunks.append({
                "content": chunk.page_content,
                "embedding": embedding,
                "metadata": chunk.metadata
            })
        
        return embedded_chunks

def process_file_with_rope(file_path: str, content_type: str) -> List[Dict[str, Any]]:
    """
    Process different file types and chunk them using ROPE
    """
    chunker = ROPEChunker()
    
    # Process based on file type
    if content_type == "application/pdf":
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        chunks = []
        for page in pages:
            page_chunks = chunker.chunk_text(
                page.page_content, 
                chunk_size=1000, 
                overlap=200
            )
            for chunk in page_chunks:
                chunk["metadata"].update({"page": page.metadata.get("page", 0)})
            chunks.extend(page_chunks)
        return chunks
        
    elif content_type == "text/plain":
        loader = TextLoader(file_path)
        documents = loader.load()
        text = "\n".join([doc.page_content for doc in documents])
        return chunker.chunk_text(text)
        
    elif content_type == "application/json":
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Convert JSON to string representation
        text = json.dumps(data, indent=2)
        chunks = chunker.chunk_text(text)
        return chunks
        
    elif content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                         "application/vnd.ms-excel"]:
        df = pd.read_excel(file_path)
        # Convert dataframe to JSON then to string
        text = df.to_json(orient="records", indent=2)
        chunks = chunker.chunk_text(text)
        return chunks
    
    else:
        raise ValueError(f"Unsupported file type: {content_type}")
