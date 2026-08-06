"""
ingest_knowledge.py

Indexador de la base de conocimiento de marketing ("cerebro") en Qdrant.
Lee todos los archivos markdown en agency/knowledge/ y los guarda en la colección 'marketing_brain' de Qdrant.
"""

import os
import glob
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "marketing_brain"


def simple_embedding(text: str) -> list[float]:
    """Generador determinista de embedding liviano (384-dim) para pruebas/dev local sin GPU/API pesada."""
    import hashlib
    vec = []
    for i in range(384):
        h = hashlib.sha256(f"{text}:{i}".encode("utf-8")).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vec.append(val)
    return vec


def run_ingestion():
    print(f"Conectando a Qdrant en {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    # Crear colección si no existe
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        print(f"Creando colección '{COLLECTION_NAME}' en Qdrant...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    knowledge_dir = os.path.dirname(os.path.abspath(__file__))
    md_files = glob.glob(os.path.join(knowledge_dir, "*.md"))

    points = []
    idx = 1
    for filepath in md_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        vector = simple_embedding(content)
        points.append(
            PointStruct(
                id=idx,
                vector=vector,
                payload={"filename": filename, "content": content},
            )
        )
        print(f"Cargado documento: {filename}")
        idx += 1

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"¡Éxito! Indexados {len(points)} documentos de conocimiento en Qdrant.")


if __name__ == "__main__":
    run_ingestion()
