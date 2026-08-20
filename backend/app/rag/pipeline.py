from sqlalchemy.orm import Session

from app.rag.embedding import generate_embedding
from app.rag.retriever import retrieve_chunks
from app.llm.client import generate_answer


def answer_question(
    db: Session,
    project_id: int,
    question: str,
    top_k: int = 5,
) -> str:

    query_embedding = generate_embedding(question)

    chunks = retrieve_chunks(
        db=db,
        project_id=project_id,
         query=question,
        top_k=top_k,
    )

    if not chunks:
        return (
            "I could not find relevant information in the project "
            "to answer this question."
        )

    context_parts = []

    for chunk in chunks:

        context_parts.append(
            f"""
File: {chunk.document.file_path}
Chunk: {chunk.chunk_index}

{chunk.content}
"""
        )

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """
You are an expert AI/ML Engineering Copilot.

You help developers understand, debug, improve,
and build machine learning systems.

You have access to retrieved context from the user's project.

IMPORTANT RULES:

1. Use the retrieved project context when answering.
2. Do not invent project-specific code or facts.
3. If the context does not contain enough information,
   explicitly say that you do not have enough information.
4. When referring to project code, mention the relevant file.
5. Explain technical reasoning clearly.
6. If you identify a bug, explain why it is a bug.
7. When suggesting code changes, explain the change.
"""

    user_prompt = f"""
PROJECT CONTEXT:

{context}


DEVELOPER QUESTION:

{question}


INSTRUCTIONS:

Answer the developer's question using the project context above.

If the answer can be determined from the code,
explain the relevant code and file.

If the retrieved context is insufficient,
say so instead of guessing.
"""

    return generate_answer(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )