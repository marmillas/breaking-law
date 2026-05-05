from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from breaking_law.identity.router import router as auth_router
from breaking_law.identity.oauth_router import router as oauth_router
from breaking_law.documents.router import router as documents_router
from breaking_law.documents.editor_router import router as editor_router
from breaking_law.crm.clients_router import router as clients_router
from breaking_law.crm.matters_router import router as matters_router
from breaking_law.crm.notifications_router import router as notifications_router
from breaking_law.api.notifications import router as sse_notifications_router
from breaking_law.search.router import router as search_router
from breaking_law.search.retrieval_router import router as retrieval_router
from breaking_law.search.rag_router import router as rag_router
from breaking_law.timekeeping.time_router import router as time_router
from breaking_law.timekeeping.deadline_router import router as deadlines_router
from breaking_law.timekeeping.calendar_router import router as calendar_router
from breaking_law.retention.router import router as retention_router
from breaking_law.shared.config import Config

cfg = Config()

app = FastAPI(
    title="Breaking Law API",
    description="AI powered API for legal document generation and automation",
    version="0.1.0",
)

# CORS middleware — must be added before routes
origins = [origin.strip() for origin in cfg.FRONTEND_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)

# Include routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(clients_router)
app.include_router(matters_router)
app.include_router(search_router)
app.include_router(retrieval_router)
app.include_router(rag_router)
app.include_router(time_router)
app.include_router(deadlines_router)
app.include_router(notifications_router)
app.include_router(sse_notifications_router)
app.include_router(retention_router)
app.include_router(oauth_router)
app.include_router(editor_router)
app.include_router(calendar_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Breaking Law API"}
