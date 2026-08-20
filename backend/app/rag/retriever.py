from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.rag.embedding import generate_embedding


def retrieve_chunks(
    db: Session,
    project_id: int,
    query: str,
    top_k: int = 5,
) -> list[DocumentChunk]:

    query_embedding = generate_embedding(query)

    statement = (
        select(DocumentChunk)
        .join(DocumentChunk.document)
        .where(
            DocumentChunk.document.has(
                project_id=project_id
            )
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(
                query_embedding
            )
        )
        .limit(top_k)
    )

    results = db.execute(
        statement
    ).scalars().all()

    return results