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
        """Add material to the vector store with automatic chunking."""
        if not self.enabled:
            return
        if not text.strip():
            raise ValueError("Material content is empty")
        
        # Split into chunks
        chunks = split_into_chunks(text, size=500, overlap=50)
        if not chunks:
            return
        
        # Create metadata for each chunk
        timestamp = datetime.utcnow().isoformat()
        source = metadata.get("source", "unknown")
        language = metadata.get("language", "unknown")
        
        chunk_ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id or str(uuid4())}_chunk_{i}"
            chunk_ids.append(chunk_id)
            metadatas.append({
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

    def query_materials(
        self,
        query_text: str,
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
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_criteria,
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
                    })
            
            return evidence_list
        except Exception:
            return []


rag_manager = RAGManager()
