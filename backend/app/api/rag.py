from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.chat_service import ask_project
from app.services.chat_service import get_chat_history

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.get("/projects/{project_id}/chat/history")
def chat_history(
    project_id: int,
    db: Session = Depends(get_db),
):

    return {
        "project_id": project_id,
        "messages": get_chat_history(
            db=db,
            project_id=project_id,
        ),
    }

@router.post("/projects/{project_id}/chat")
def chat_with_project(
    project_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
):

    answer = ask_project(
        db=db,
        project_id=project_id,
        question=request.question,
    )

    return {
        "project_id": project_id,
        "question": request.question,
        "answer": answer,
    }