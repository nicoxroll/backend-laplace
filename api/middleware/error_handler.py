from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
import uuid

async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno",
            "request_id": request.state.request_id,
            "error_type": exc.__class__.__name__
        }
    )

async def add_request_id(request: Request, call_next):
    request.state.request_id = uuid.uuid4()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(request.state.request_id)
    return response

# En lugar de usar el decorador, definimos una función para registrar los handlers
def add_error_handlers(app: FastAPI):
    app.middleware("http")(add_request_id)
    app.exception_handler(Exception)(global_exception_handler)