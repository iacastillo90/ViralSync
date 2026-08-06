"""
test_ingest_knowledge.py

Pruebas unitarias para la carga de documentos de conocimiento.
"""

import os
import glob
from knowledge.ingest_knowledge import simple_embedding


def test_knowledge_markdown_files_exist():
    knowledge_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "knowledge"
    )
    md_files = glob.glob(os.path.join(knowledge_dir, "*.md"))
    assert len(md_files) >= 9  # Deben existir al menos los 9 documentos de dominio


def test_simple_embedding_consistency():
    vec1 = simple_embedding("rum_formula")
    vec2 = simple_embedding("rum_formula")
    assert vec1 == vec2
