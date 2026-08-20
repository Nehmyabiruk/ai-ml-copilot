from pathlib import Path

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.embedding import generate_embedding
from app.rag.hashing import calculate_file_hash


db = SessionLocal()


file_path = Path("test_small_ingestion.py")


text = file_path.read_text(
    encoding="utf-8"
)


file_hash = calculate_file_hash(
    file_path
)


print("File hash:", file_hash)


print("Generating embedding...")


embedding = generate_embedding(text)


print("Embedding generated.")


document = Document(
    project_id=1,
    file_name=file_path.name,
    file_path=str(file_path),
    file_type=file_path.suffix,
    content=text,
    file_hash=file_hash,
)


db.add(document)


db.flush()


print("Document ID:", document.id)


chunk = DocumentChunk(
    document_id=document.id,
    chunk_index=0,
    content=text,
    embedding=embedding,
    metadata={
        "file_path": str(file_path),
        "file_type": file_path.suffix,
        "test": True,
    },
)


db.add(chunk)


db.commit()


print("DONE.")


db.close()