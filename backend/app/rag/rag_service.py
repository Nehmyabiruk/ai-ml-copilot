from sqlalchemy.orm import Session

from app.rag.embedding import generate_embedding
from app.rag.retriever import retrieve_chunks
from app.llm.client import generate_answer


SYSTEM_PROMPT = """
You are an AI software engineering copilot.

Answer the user's question using the provided project context.

Rules:

1. Use the provided context as the primary source of truth.
2. Do not invent project details.
3. If the context does not contain enough information, say so.
4. Explain technical concepts clearly.
5. When discussing code, explain why the code works.
6. Keep the answer focused on the user's question.

Project context:

{context}
"""


def build_context(chunks):
    context_parts = []

    for chunk in chunks:
        context_parts.append(
            f"""
FILE: {chunk.document.file_path}
CHUNK: {chunk.chunk_index}

{chunk.content}
"""
        )

    return "\n".join(context_parts)


def generate_rag_answer(
    db: Session,
    project_id: int,
    question: str,
    top_k: int = 5,
):
    #query_embedding = generate_embedding(question)

    chunks = retrieve_chunks(
        db=db,
        project_id=project_id,
        query=question,
        top_k=top_k,
    )

    if not chunks:
        return {
            "answer": (
                "I could not find relevant information "
                "in this project."
            ),
            "sources": [],
        }

    context = build_context(chunks)

    system_prompt = SYSTEM_PROMPT.format(
        context=context
    )

    answer = generate_answer(
        system_prompt=system_prompt,
        user_prompt=question,
    )

    sources = []

    for chunk in chunks:
        sources.append(
            {
                "document_id": chunk.document_id,
                "file_name": chunk.document.file_name,
                "file_path": chunk.document.file_path,
                "chunk_index": chunk.chunk_index,
            }
        )

    return {
        "answer": answer,
        "sources": sources,
    }