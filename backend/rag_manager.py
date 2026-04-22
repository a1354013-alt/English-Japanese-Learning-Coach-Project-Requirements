"""RAG manager using ChromaDB with proper chunking."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import chromadb

from config import settings


def split_into_chunks(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks for better retrieval.
    
    Args:
        text: The text to split
        size: Target chunk size in characters (default 500)
        overlap: Number of overlapping characters between chunks (default 50)
    
    Returns:
        List of text chunks with overlap for context preservation
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + size
        chunk = text[start:end]
        
        # Try to break at sentence boundary if not at end
        if end < text_len:
            # Look for sentence endings in the last 100 chars
            search_start = max(start, end - 100)
            for sep in ['。\n', '.\n', '!\n', '?\n', '\n\n']:
                idx = chunk.rfind(sep, search_start - start)
                if idx > size // 2:  # Only break if we're past halfway
                    end = start + idx + len(sep)
                    chunk = text[start:end]
                    break
        
        chunks.append(chunk.strip())
        start = end - overlap if end < text_len else text_len
    
    return [c for c in chunks if c]  # Remove empty chunks


def _and_where(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a Chroma 'where' filter that is compatible with versions requiring a single top-level operator.

    Chroma's validation expects 'where' to be either:
      - a single field equality dict: {"user_id": "u1"}, OR
      - a single operator dict: {"$and": [{"user_id": "u1"}, {"language": "EN"}]}
    """
    clauses = [c for c in clauses if c]
    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


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

    def add_material(
        self,
        text: str,
        metadata: Dict[str, Any],
        *,
        doc_id: Optional[str] = None,
        user_id: str,
    ) -> str:
        """Add material to the vector store with automatic chunking.

        Returns the material doc_id (stable identifier across chunks).
        """
        if not self.enabled:
            raise RuntimeError(self.init_error or "RAG is disabled")
        if not text.strip():
            raise ValueError("Material content is empty")

        # Split into chunks
        chunks = split_into_chunks(text, size=500, overlap=50)
        if not chunks:
            raise ValueError("Material content produced no chunks")

        # Create metadata for each chunk
        timestamp = datetime.utcnow().isoformat()
        source = str(metadata.get("source", "unknown"))
        language = str(metadata.get("language", "unknown"))
        material_id = doc_id or str(uuid4())

        chunk_ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{material_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            metadatas.append({
                "doc_id": material_id,
                "user_id": user_id,
                "source": source,
                "chunk_index": i,
                "language": language,
                "uploaded_at": timestamp,
                "total_chunks": len(chunks),
            })

        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=chunk_ids,
        )
        return material_id

    def query_materials(
        self,
        query_text: str,
        *,
        user_id: str,
        language: str,
        n_results: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query materials and return chunks with evidence metadata.
        
        Returns:
            List of dicts with 'text', 'source', 'chunk_index' keys
        """
        if not self.enabled:
            return []
        try:
            clauses: List[Dict[str, Any]] = [{"user_id": user_id}, {"language": language}]
            if filter_criteria:
                # Support simple multi-field dicts by splitting into equality clauses.
                for k, v in filter_criteria.items():
                    clauses.append({str(k): v})
            where = _and_where(clauses)
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas"],
            )
            
            docs = results.get("documents") or []
            metas = results.get("metadatas") or []
            
            if not docs or not docs[0]:
                return []
            
            # Return structured evidence with metadata
            evidence_list = []
            for i, doc in enumerate(docs[0]):
                if doc:
                    metadata = metas[0][i] if metas and i < len(metas[0]) else {}
                    evidence_list.append({
                        "text": str(doc),
                        "source": metadata.get("source", "unknown"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "doc_id": metadata.get("doc_id"),
                    })

            return evidence_list
        except Exception:
            return []

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        clauses: List[Dict[str, Any]] = [{"user_id": user_id}]
        if language:
            clauses.append({"language": language})
        where = _and_where(clauses)
        try:
            results = self.collection.get(where=where, include=["metadatas"])
            metas = results.get("metadatas") or []
            by_doc: Dict[str, Dict[str, Any]] = {}
            for meta in metas:
                if not isinstance(meta, dict):
                    continue
                doc_id = str(meta.get("doc_id") or "")
                if not doc_id:
                    continue
                existing = by_doc.get(doc_id)
                if existing is None:
                    by_doc[doc_id] = {
                        "doc_id": doc_id,
                        "source": meta.get("source", "unknown"),
                        "language": meta.get("language", "unknown"),
                        "uploaded_at": meta.get("uploaded_at"),
                        "total_chunks": meta.get("total_chunks"),
                    }
            # Sort newest first if timestamps exist
            return sorted(by_doc.values(), key=lambda x: str(x.get("uploaded_at") or ""), reverse=True)
        except Exception:
            return []

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        if not self.enabled:
            return False

        # Chroma's delete(where=...) is idempotent and may not error when nothing matches.
        # For API correctness we must distinguish "not found" vs "deleted".
        where = _and_where([{"user_id": user_id}, {"doc_id": doc_id}])
        try:
            existing = self.collection.get(where=where, include=["metadatas"])
        except Exception as err:  # pragma: no cover - defensive: chroma query failure
            raise RuntimeError(f"RAG lookup failed: {err}") from err

        ids = existing.get("ids") or []
        if not ids:
            return False

        try:
            self.collection.delete(where=where)
        except Exception as err:
            raise RuntimeError(f"RAG delete failed: {err}") from err

        return True


rag_manager = RAGManager()
