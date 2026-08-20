from app.core.database import SessionLocal
from app.rag.ingestion import ingest_project


db = SessionLocal()

project_id = 1

project_path = r"C:\Users\Azeb\commodity-predict"

chunks = ingest_project(
    db=db,
    project_id=project_id,
    project_path=project_path,
)

print("Chunks inserted:", chunks)

db.close()