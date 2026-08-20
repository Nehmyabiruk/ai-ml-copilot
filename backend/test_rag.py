from app.core.database import SessionLocal
from app.rag.pipeline import answer_question


db = SessionLocal()


answer = answer_question(
    db=db,
    project_id=1,
    question="What does this project use XGBoost for?",
    top_k=5,
)


print("=" * 80)
print(answer)
print("=" * 80)


db.close()