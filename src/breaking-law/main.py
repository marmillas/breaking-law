from fastapi import FastAPI
from pydantic import BaseModel
from src.breaking-law.routers import documents, clients, matters

app = FastAPI(
    title="Breaking Law API",
    description="AI powered API for legal document generation and automation",
    version="0.1.0",
)

# Include routers
app.include_router(documents.router)
app.include_router(clients.router)
app.include_router(matters.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Breaking Law API"}