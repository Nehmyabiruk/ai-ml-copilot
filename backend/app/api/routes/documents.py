from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.document import Document
from app.core.auth import get_current_user, require_project_owner
from app.models.github import AppUser


router = APIRouter(
    prefix="/projects",
    tags=["Documents"],
)


class DocumentResponse:
    def __init__(self, document: Document):
        self.id = document.id
        self.file_name = document.file_name
        self.file_path = document.file_path
        self.file_type = document.file_type
        self.created_at = document.created_at.isoformat() if document.created_at else None
        self.chunks_count = len(document.chunks) if document.chunks else 0

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "created_at": self.created_at,
            "chunks_count": self.chunks_count,
        }


@router.get("/{project_id}/documents")
def get_project_documents(
    project_id: int,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    """Get all documents for a project."""
    require_project_owner(project_id, user, db)
    documents = db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    ).scalars().all()

    return {
        "documents": [DocumentResponse(doc).to_dict() for doc in documents],
        "total": len(documents),
    }
