from fastapi import APIRouter, HTTPException
import json
from typing import Any
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.github_service import (
    push_changes_to_github,
)


router = APIRouter()


class PushRequest(BaseModel):
    repository_url: str
    commit_message: str
    changes: list[dict]


@router.post("/{project_id}/push")
def push_project_changes(
    project_id: int,
    request: PushRequest,
):
    try:
        result = push_changes_to_github(
            repository_url=request.repository_url,
            commit_message=request.commit_message,
            changes=request.changes,
        )

        return result

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )