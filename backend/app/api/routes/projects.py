from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import create_project
from app.core.auth import get_current_user
from app.models.github import AppUser


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_endpoint(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    project = create_project(
        db=db,
        project_data=project_data,
    )
    project.owner_user_id = user.id
    db.commit()
    db.refresh(project)
    return project
@router.delete("/{project_id}/files/{document_id}", status_code=status.HTTP_200_OK)
def delete_file_endpoint(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_db),
):
    # Find the document belonging to this specific project
    document = db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.id == document_id
        )
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="File not found in this project")

    # Delete it! (Your DB should automatically cascade delete child DocumentChunks)
    db.delete(document)
    db.commit()

    return {"status": "success", "message": f"Document {document_id} and its chunks deleted."}

