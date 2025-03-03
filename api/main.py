from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
import uvicorn
from pydantic_settings import BaseSettings  # Usar pydantic_settings

# Comenta esta línea problemática
# from middleware.error_handler import add_error_handlers

# Definir add_error_handlers directamente
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno",
            "request_id": getattr(request.state, 'request_id', str(uuid.uuid4())),
            "error_type": exc.__class__.__name__
        }
    )

async def add_request_id(request: Request, call_next):
    request.state.request_id = uuid.uuid4()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(request.state.request_id)
    return response

def add_error_handlers(app: FastAPI):
    app.middleware("http")(add_request_id)
    app.exception_handler(Exception)(global_exception_handler)

# El resto de tu código
from config import Settings
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

# Importar las rutas
from routers import auth, knowledge, users, agents
from routers.system_agents import router as system_agents_router
from routers.user_knowledge import router as user_knowledge_router

app.include_router(auth.router)
app.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(system_agents_router, prefix="/api/system-agents", tags=["system_agents"])
app.include_router(user_knowledge_router, prefix="/api/users", tags=["user_knowledge"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Laplace API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
