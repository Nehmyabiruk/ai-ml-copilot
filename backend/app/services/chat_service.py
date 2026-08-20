from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage
from app.rag.retriever import retrieve_chunks
from app.rag.embedding import generate_embedding
from app.llm.client import generate_answer


MAX_HISTORY_MESSAGES = 20
MAX_CONTEXT_CHUNKS = 8


def get_chat_history(
    db: Session,
    project_id: int,
) -> list[dict[str, str]]:

    statement = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )

    messages = db.execute(statement).scalars().all()

    messages.reverse()

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]


def save_message(
    db: Session,
    project_id: int,
    role: str,
    content: str,
) -> ChatMessage:

    message = ChatMessage(
        project_id=project_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.flush()

    return message


def build_project_context(
    db: Session,
    project_id: int,
    question: str,
) -> str:

    query_embedding = generate_embedding(question)

    chunks = retrieve_chunks(
        db=db,
        project_id=project_id,
        query_embedding=query_embedding,
        top_k=MAX_CONTEXT_CHUNKS,
    )

    if not chunks:
        return "No relevant project files were found."

    context_parts = []

    for chunk in chunks:

        document = chunk.document

        context_parts.append(
            f"""
FILE: {document.file_path}

CONTENT:
{chunk.content}
"""
        )

    return "\n---\n".join(context_parts)


def ask_project(
    db: Session,
    project_id: int,
    question: str,
) -> str:

    history = get_chat_history(
        db=db,
        project_id=project_id,
    )

    project_context = build_project_context(
        db=db,
        project_id=project_id,
        question=question,
    )

    system_prompt = """
You are an AI software engineering copilot.

You help users understand, debug, modify, improve,
and build software projects.

You have access to:

1. Project files retrieved from the project's private RAG database.
2. Conversation history.
3. External web search.

IMPORTANT RULES:

- Never invent project code.
- Prefer the provided project context when answering
  questions about the user's project.
- Use web search when the question requires current,
  external, or up-to-date information.
- When fixing code, explain the problem and provide
  the complete corrected code when appropriate.
- Keep project information isolated.
- Never use information from another project.
- Clearly distinguish project information from external
  information.
- If the provided project context is insufficient,
  say what is missing instead of pretending.
- For technical answers, give practical implementation
  steps and production-quality code.

PROJECT CONTEXT:

""" + project_context

    save_message(
        db=db,
        project_id=project_id,
        role="user",
        content=question,
    )

    answer = generate_answer(
        system_prompt=system_prompt,
        user_prompt=question,
        history=history,
    )

    save_message(
        db=db,
        project_id=project_id,
        role="assistant",
        content=answer,
    )

    db.commit()

    return answer