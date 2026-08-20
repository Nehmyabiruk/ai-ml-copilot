import hashlib
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk

from app.ingestion.parser import parse_file
from app.ingestion.chunker import chunk_code

from app.rag.hashing import calculate_file_hash
from app.rag.embedding import generate_embedding

from app.ingestion.github import (
    clone_repository,
    discover_files,
    is_data_file,
)

# --- FUNCTION 1: Handles single files and replaces modified versions ---
def ingest_file(
    db: Session,
    project_id: int,
    file_path: Path,
    repository_root: Path,
) -> Document | None:

    relative_path = str(
        file_path.relative_to(
            repository_root
        )
    )

    data_file = is_data_file(file_path, repository_root)
    # Do not read or hash the contents of potentially large dataset files.
    file_hash = (
        hashlib.sha256(f"data:{relative_path}:{file_path.stat().st_size}:{file_path.stat().st_mtime_ns}".encode()).hexdigest()
        if data_file else calculate_file_hash(file_path)
    )

    existing = db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.file_path == relative_path,
        )
    ).scalar_one_or_none()

    if existing:
        if existing.file_hash == file_hash:
            return existing
        
        db.delete(existing)
        db.flush()

        # ---------- safe content reading ----------
    if data_file:
        content = (
            f"Dataset file available at {relative_path}. "
            f"Filename: {file_path.name}. Contents were intentionally not indexed."
        )
    else:
        content = parse_file(file_path)

        # PostgreSQL cannot store NUL (0x00) bytes.
        # This usually appears when a file is actually UTF-16.
        if "\x00" in content:
            # Re-read the file properly
            raw = file_path.read_bytes()
            try:
                content = raw.decode("utf-16").replace("\x00", "")
            except UnicodeDecodeError:
                content = raw.decode("utf-8", errors="replace").replace("\x00", "")
        else:
            content = content.replace("\x00", "")   # extra safety
    # -----------------------------------------
    document = Document(
        project_id=project_id,
        file_name=file_path.name,
        file_path=relative_path,
        file_type=file_path.suffix,
        content=content,
        file_hash=file_hash,
    )

    db.add(document)
    db.flush()

    chunks = chunk_code(
        content
    )

    for index, chunk_text in enumerate(chunks):

        embedding = generate_embedding(
            chunk_text
        )

        document_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk_text,
            embedding=embedding,
            chunk_metadata={
                "file_path": relative_path,
                "file_type": file_path.suffix,
                "project_id": project_id,
            },
        )

        db.add(document_chunk)

    return document


# --- FUNCTION 2: Handles downloading from GitHub and looping through files ---
def ingest_github_repository(
    db: Session,
    project_id: int,
    repository_url: str,
) -> int:

    temporary_directory = clone_repository(
        repository_url
    )

    try:
        repository_root = Path(
            temporary_directory.name
        )

        return ingest_repository_directory(db, project_id, repository_root)

    except Exception:
        db.rollback()
        raise

    finally:
        temporary_directory.cleanup()


def ingest_repository_directory(db: Session, project_id: int, repository_root: Path) -> int:
    """Ingest an already-authorized repository checkout/archive."""
    try:
        count = 0
        for file_path in discover_files(repository_root):
            if ingest_file(db, project_id, file_path, repository_root):
                count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
