from sentence_transformers import SentenceTransformer

Model_Name ="sentence-transformers/all-MiniLM-L6-v2"
Model = SentenceTransformer(Model_Name)
def generate_embedding (text:str) -> list[float]:
    embedding = Model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()

