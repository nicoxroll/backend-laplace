from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
import uvicorn

from config import Settings
from database import engine, Base
from middleware.error_handler import add_error_handlers
from routers import analysis, auth, agents, knowledge, repos, chats, agent_knowledge

# Crear todas las tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Laplace API",
    description="API for the Laplace project"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar manejadores de errores
add_error_handlers(app)

# Incluir rutas
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(repos.router, prefix="/api/repos", tags=["repositories"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(agent_knowledge.router, prefix="/api/agent-knowledge", tags=["agent-knowledge"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)