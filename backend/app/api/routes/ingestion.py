from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ingestion.service import (
    ingest_github_repository,
    ingest_repository_directory,
)
from app.core.auth import get_current_user, require_project_owner
from app.models.github import AppUser
from app.github.service import GitHubServiceError, download_repository_archive, validate_github_url, get_public_repository_info


router = APIRouter(
    prefix="/projects",
    tags=["Ingestion"],
)


class GitHubIngestionRequest(BaseModel):
    repository_url: str


@router.post("/{project_id}/github")
def ingest_github(
    project_id: int,
    request: GitHubIngestionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    try:
        project = require_project_owner(project_id, user, db)

        if not project.github_repository:
            raise HTTPException(403, "Select a GitHub repository for this project first.")

        installation = project.github_repository.installation

        if installation.user_id != user.id:
            raise HTTPException(403, "This repository is not authorized for the current user.")

        if not installation.access_token:
            raise HTTPException(401, "GitHub is not connected. Please connect GitHub first.")

        if request.repository_url and request.repository_url != project.repository_url:
            raise HTTPException(403, "Repository URL does not match the authorized project repository.")

        archive = download_repository_archive(
            access_token=installation.access_token,
            full_name=project.github_repository.full_name,
            branch=project.github_repository.default_branch or "main",
        )

        try:
            from pathlib import Path
            root = next(path for path in Path(archive.name).iterdir() if path.is_dir())
            count = ingest_repository_directory(db, project_id, root)
        finally:
            archive.cleanup()

        return {
            "message": "Repository ingested successfully.",
            "files_processed": count,
        }

    except HTTPException:
        raise
    except GitHubServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{project_id}/ingest-repo")
def ingest_public_repo(
    project_id: int,
    request: GitHubIngestionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_current_user),
):
    project = require_project_owner(project_id, user, db)
    try:
        full_name = validate_github_url(request.repository_url)
        public_info = get_public_repository_info(full_name)
        count = ingest_github_repository(db, project_id, request.repository_url)
        project.repository_url = f"https://github.com/{public_info['full_name']}.git"
        db.commit()
        return {
            "repository": {
                "full_name": public_info["full_name"],
                "default_branch": public_info["default_branch"],
            },
            "ingestion": {
                "status": "completed",
                "files_ingested": count,
            },
        }
    except HTTPException:
        raise
    except GitHubServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
