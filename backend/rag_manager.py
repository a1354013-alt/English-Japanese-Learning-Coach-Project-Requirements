"""RAG manager using ChromaDB."""
from typing import Any, Dict, List, Optional
from uuid import uuid4

import chromadb

from config import settings


class RAGManager:
    def __init__(self) -> None:
        self.enabled = True
        self.init_error: Optional[str] = None
        try:
            self.client = chromadb.PersistentClient(path=str(settings.chroma_db_path))
            self.collection = self.client.get_or_create_collection(name="learning_materials")
        except Exception as err:
            self.enabled = False
            self.init_error = str(err)

    def add_material(self, text: str, metadata: Dict[str, Any], doc_id: Optional[str] = None) -> None:
        if not self.enabled:
            return
        if not text.strip():
            raise ValueError("Material content is empty")
        self.collection.add(documents=[text], metadatas=[metadata], ids=[doc_id or str(uuid4())])

    def query_materials(
        self,
        query_text: str,
        n_results: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        if not self.enabled:
            return []
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_criteria,
            )
            docs = results.get("documents") or []
            if not docs:
                return []
            return [str(item) for item in docs[0] if item]
        except Exception:
            return []


rag_manager = RAGManager()
