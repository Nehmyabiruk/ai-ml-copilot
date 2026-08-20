import json
import hashlib
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.ingestion.chunker import chunk_code
from app.rag.embedding import generate_embedding
from app.services.code_audit import scan_project
from app.services.code_repair import generate_repair
from app.core.auth import get_current_user, require_project_owner
from app.models.github import AppUser


router = APIRouter(prefix="/projects", tags=["Code repair"])


class RepairRequest(BaseModel):
    file_path: str | None = None
    issue: dict[str, Any] | None = None


class ApplyRepairRequest(BaseModel):
    file_path: str
    fixed_code: str


def _find_file_from_trace(db: Session, project_id: int, issue: dict[str, Any]) -> str | None:
    """Match a path mentioned in a traceback to a file in this project only."""
    message = str(issue.get("message", ""))
    candidates = re.findall(r'File ["\']([^"\']+)["\']', message)
    documents = db.query(Document).filter(Document.project_id == project_id).all()
    for candidate in candidates:
        normalised = candidate.replace("\\", "/")
        for document in documents:
            if normalised.endswith(document.file_path.replace("\\", "/")):
                return document.file_path
    return None


@router.post("/{project_id}/audit")
def audit_project(project_id: int, db: Session = Depends(get_db), user: AppUser = Depends(get_current_user)):
    require_project_owner(project_id, user, db)
    documents = db.query(Document.id).filter(Document.project_id == project_id).first()
    if not documents:
        raise HTTPException(404, "No repository files were found. Ingest a repository first.")
    issues = scan_project(db, project_id)
    return {"issues": issues, "total": len(issues)}


@router.post("/{project_id}/repair")
def repair_project(project_id: int, request: RepairRequest, db: Session = Depends(get_db), user: AppUser = Depends(get_current_user)):
    require_project_owner(project_id, user, db)
    issue = request.issue or {}
    file_path = request.file_path or _find_file_from_trace(db, project_id, issue)
    if not file_path:
        first_code_file = (
            db.query(Document)
            .filter(Document.project_id == project_id, Document.file_type.in_([".py", ".js", ".jsx", ".ts", ".tsx"]))
            .first()
        )
        if not first_code_file:
            raise HTTPException(404, "No code files were found in this repository.")
        file_path = first_code_file.file_path
    try:
        return generate_repair(db, project_id, file_path, issue)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Could not generate a repair: {exc}") from exc


@router.post("/{project_id}/apply-repair")
def apply_repair(project_id: int, request: ApplyRepairRequest, db: Session = Depends(get_db), user: AppUser = Depends(get_current_user)):
    """Replace the indexed source and rebuild its RAG chunks before a GitHub push."""
    require_project_owner(project_id, user, db)
    document = (
        db.query(Document)
        .filter(Document.project_id == project_id, Document.file_path == request.file_path)
        .first()
    )
    if not document:
        raise HTTPException(404, "The repair file is not part of this repository.")
    if not request.fixed_code.strip():
        raise HTTPException(422, "Fixed code cannot be empty.")

    try:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        document.content = request.fixed_code
        document.file_hash = hashlib.sha256(request.fixed_code.encode("utf-8")).hexdigest()
        for index, chunk_text in enumerate(chunk_code(request.fixed_code)):
            db.add(DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_text,
                embedding=generate_embedding(chunk_text),
                chunk_metadata={"file_path": document.file_path, "file_type": document.file_type, "project_id": project_id},
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"message": f"Applied repair to {document.file_path} and refreshed its RAG index."}
