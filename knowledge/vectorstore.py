import faiss
import numpy as np
import pickle
from pathlib import Path


class FaissVectorStore:
    def __init__(self, dim: int, index_path="data/vector.index"):
        self.dim = dim
        self.index_path = index_path
        self.index = faiss.IndexFlatL2(dim)
        self.documents = []

    def add(self, embeddings, documents):
        self.index.add(np.array(embeddings).astype("float32"))
        self.documents.extend(documents)

    def search(self, query_embedding, top_k=3):
        distances, indices = self.index.search(
            np.array([query_embedding]).astype("float32"),
            top_k
        )
        return [self.documents[i] for i in indices[0]]

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.index_path + ".docs", "wb") as f:
            pickle.dump(self.documents, f)

    def load(self):
        if Path(self.index_path).exists():
            self.index = faiss.read_index(self.index_path)
            with open(self.index_path + ".docs", "rb") as f:
                self.documents = pickle.load(f)
