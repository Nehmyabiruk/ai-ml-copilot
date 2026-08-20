from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.projects import router as projects_router
from app.api.routes.documents import router as documents_router
from app.core.database import Base, engine
from app.core.config import settings
from app.api.routes.code_repair import router as repair_router
from app.api.routes.github import router as github_router

app = FastAPI(
    title="AI/ML Copilot API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(ingestion_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(repair_router)
app.include_router(github_router)
