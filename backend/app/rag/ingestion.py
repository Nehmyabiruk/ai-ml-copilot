from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.chunker import chunk_python_code
from app.rag.embedding import generate_embedding
from app.rag.hashing import calculate_file_hash


SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
}


def read_file(path: Path) -> str:

    return path.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )


def chunk_text(
    text: str,
    chunk_size: int = 1000,
) -> list[str]:

    return [
        text[i:i + chunk_size]
        for i in range(
            0,
            len(text),
            chunk_size,
        )
    ]


def ingest_project(
    db: Session,
    project_id: int,
    project_path: str,
) -> int:

    root = Path(project_path)

    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    current_file_paths = {
        str(path.relative_to(root))
        for path in files
    }

    existing_documents = (
        db.query(Document)
        .filter(
            Document.project_id == project_id
        )
        .all()
    )

    for document in existing_documents:

        if document.file_path not in current_file_paths:

            db.delete(document)

    db.flush()

    total_chunks = 0

    for path in files:

        relative_path = str(
            path.relative_to(root)
        )

        content = read_file(path)

        file_hash = calculate_file_hash(path)

        existing_document = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.file_path == relative_path,
            )
            .first()
        )

        if existing_document:

            if existing_document.file_hash == file_hash:

                total_chunks += len(
                    existing_document.chunks
                )

                continue

            db.delete(existing_document)

            db.flush()

        document = Document(
            project_id=project_id,
            file_name=path.name,
            file_path=relative_path,
            file_type=path.suffix.lower(),
            content=content,
            file_hash=file_hash,
        )

        db.add(document)

        db.flush()

        if path.suffix.lower() == ".py":

            code_chunks = chunk_python_code(
                content
            )

            chunks = [
                {
                    "content": chunk.content,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "symbol": chunk.symbol,
                }
                for chunk in code_chunks
            ]

        else:

            text_chunks = chunk_text(
                content
            )

            chunks = [
                {
                    "content": chunk,
                    "start_line": None,
                    "end_line": None,
                    "symbol": None,
                }
                for chunk in text_chunks
            ]

        if not chunks:

            continue

        texts_to_embed = [
            chunk["content"]
            for chunk in chunks
        ]

        all_embeddings = generate_embedding(
            texts_to_embed
        )

        for index, chunk in enumerate(chunks):

            embedding = all_embeddings[index]

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk["content"],
                embedding=embedding,
                chunk_metadata={
                    "file_path": relative_path,
                    "file_type": path.suffix.lower(),
                    "symbol": chunk["symbol"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                },
            )

            db.add(document_chunk)

            total_chunks += 1
            db.commit()

    return total_chunks