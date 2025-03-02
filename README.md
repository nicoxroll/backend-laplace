# Laplace: AI-Powered Knowledge & Code Analysis Platform

Laplace is an advanced RAG (Retrieval-Augmented Generation) platform designed for developers and teams to analyze codebases, documentation, and knowledge repositories with natural language queries. The system integrates with GitHub/GitLab and supports document processing to create an intelligent assistant tailored to your specific context.

![Laplace Architecture](graph.mermaid)

## System Overview

Laplace operates through a coordinated flow of components:

### 1. User Interaction Layer

- **Analyze Interface**: Submit queries to analyze code and documentation
- **Chat Interface**: Conversational interactions with specialized AI agents
- **Knowledge Manager**: Upload and manage documents and knowledge sources
- **Repo Indexer**: Connect and index GitHub/GitLab repositories
- **Auth Interface**: Secure authentication via OAuth providers

### 2. Processing & Intelligence Layer

- **API Gateway**: Central entry point for all requests
- **RAG Engine**: Coordinates retrieval and generation processes
- **BERT Integration**: Query expansion to improve search relevance
- **Model Router**: Directs requests to appropriate AI models
- **Cache Manager**: Optimizes performance through Redis caching

### 3. Data Processing Pipeline

- **File Processor**: Ingests documents using ROPE chunking for optimal context preservation
- **Vector Optimizer**: Enhances embedding quality through batching and compression
- **Indexing Service**: Processes code repositories for semantic search
- **GitHub/GitLab Client**: Securely connects to source code platforms

### 4. Data & AI Services

- **PostgreSQL**: Stores user data and metadata
- **Weaviate**: Vector database for efficient hybrid search
- **Redis**: Session management and result caching
- **Ollama Agents**: Specialized AI models for different use cases:
  - Code analysis (deepseek)
  - Chat interactions (llama3)
  - Document processing (llama2)

## Application Flow

1. **Authentication Flow**
   - Users authenticate through GitHub or GitLab
   - OAuth tokens are exchanged and validated
   - User sessions are established in Redis
2. **Knowledge Ingestion**

   - **Document Upload**: Files are processed, chunked with ROPE, and vectorized
   - **Repository Indexing**: Code repos are cloned, analyzed, and indexed
   - All vectors are stored in Weaviate with appropriate metadata

3. **Query Processing**

   - User submits natural language query
   - BERT service expands query with semantically related terms
   - Hybrid search combines vector similarity and keyword matching
   - Multiple search strategies are fused for optimal retrieval
   - Relevant context is retrieved from Weaviate

4. **Response Generation**
   - Retrieved context is formatted with the query
   - Specialized Ollama model generates comprehensive response
   - Results are cached for improved performance

## Key Technical Features

- **Hybrid Search**: Combines vector similarity and keyword search for better results
- **Query Expansion**: Enhances queries with related terms via BERT
- **ROPE Chunking**: Maintains semantic coherence during document processing
- **Reciprocal Rank Fusion**: Merges multiple search strategies for optimal retrieval
- **Vector Optimization**: Improves embedding quality and efficiency

## Deployment

Laplace uses Docker Compose for deployment:

```bash
docker-compose up -d
```
