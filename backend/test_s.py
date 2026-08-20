from app.rag.embedding import generate_embedding


text = """
This is a small machine learning project.
It uses XGBoost for prediction.
"""


print("Starting embedding...")

embedding = generate_embedding(text)

print("Embedding finished.")

print("Dimensions:", len(embedding))

print("First 5:", embedding[:5])