from app.rag.embedding import generate_embedding

text = "XGBoost predicts Ethiopian commodity prices using historical features."
embedding = generate_embedding(text)


print("Dimensions:", len(embedding))
print("First 5 values:", embedding[:5])