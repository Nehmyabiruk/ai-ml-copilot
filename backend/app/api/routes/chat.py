from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)
from app.rag.rag_service import generate_rag_answer
from app.core.auth import get_current_user, require_project_owner
from app.models.github import AppUser


router = APIRouter(
    prefix="/projects",
    tags=["RAG Chat"],
)


@router.post(
    "/{project_id}/chat",
    response_model=ChatResponse,
)
def chat_with_project(
    project_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    require_project_owner(project_id, user, db)
    return generate_rag_answer(
        db=db,
        project_id=project_id,
        question=request.question,
    )
