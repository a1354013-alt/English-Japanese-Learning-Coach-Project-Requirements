"""
RAG (Retrieval-Augmented Generation) manager using ChromaDB
"""
import chromadb
import uuid
from typing import List, Dict, Any, Optional
from config import settings

class RAGManager:
    """RAG manager for language learning materials"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.client.get_or_create_collection(name="learning_materials")
        
    def add_material(self, text: str, metadata: Dict[str, Any], doc_id: Optional[str] = None):
        """Add learning material to the vector database (P1 Fix: Optional doc_id)"""
        if not doc_id:
            doc_id = str(uuid.uuid4())
            
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
    def query_materials(self, query_text: str, n_results: int = 3, filter_criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        """Query relevant materials"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_criteria
        )
        return results['documents'][0] if results['documents'] else []

rag_manager = RAGManager()
