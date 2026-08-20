from app.core.database import SessionLocal
from app.rag.retriever import retrieve_chunks


db = SessionLocal()


project_id = 1

query = "How does the project use XGBoost for prediction?"


results = retrieve_chunks(
    db=db,
    project_id=project_id,
    query=query,
    top_k=5,
)


for result in results:

    print("=" * 80)

    print(
        f"Chunk ID: {result.id}"
    )

    print(
        f"Document ID: {result.document_id}"
    )

    print(
        result.content
    )


db.close()