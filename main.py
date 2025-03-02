from fastapi import FastAPI
from api.routers import auth
from database.db import engine
from database import models

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Laplace API")

# Register routes
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Laplace API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
