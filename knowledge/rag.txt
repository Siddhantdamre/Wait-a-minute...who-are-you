from pathlib import Path
from models.embeddings import EmbeddingModel
from knowledge.vectorstore import FaissVectorStore


class CulturalRAG:
    def __init__(self, doc_path="knowledge/documents"):
        self.embedder = EmbeddingModel()
        self.vectorstore = FaissVectorStore(dim=384)
        self._load_documents(doc_path)

    def _load_documents(self, doc_path):
        texts = []
        documents = []

        for file in Path(doc_path).glob("*.txt"):
            content = file.read_text(encoding="utf-8")
            texts.append(content)
            documents.append({
                "source": file.name,
                "content": content
            })

        if texts:
            embeddings = self.embedder.embed(texts)
            self.vectorstore.add(embeddings, documents)
            self.vectorstore.save()

    def retrieve(self, intent: dict, top_k=3):
        query = f"{intent.get('theme', '')} {intent.get('region', '')}"
        query_embedding = self.embedder.embed([query])[0]
        return self.vectorstore.search(query_embedding, top_k)
