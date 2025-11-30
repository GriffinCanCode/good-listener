import logging
import os
import time
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, persistence_path: str = "data/chroma_db"):
        self.persistence_path = persistence_path
        self._ensure_data_dir()
        
        try:
            self.client = chromadb.PersistentClient(path=self.persistence_path)
            self.collection = self.client.get_or_create_collection(
                name="user_context",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"MemoryService initialized at {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryService: {e}")
            self.client = None
            self.collection = None

    def _ensure_data_dir(self):
        if not os.path.exists(self.persistence_path):
            os.makedirs(self.persistence_path, exist_ok=True)

    def add_memory(self, text: str, source: str, metadata: Optional[Dict] = None):
        """
        Add a text chunk to the vector store.
        
        Args:
            text: The text content to embed and store.
            source: 'audio', 'screen', or 'user_query'.
            metadata: Additional metadata (timestamp, window_title, etc.).
        """
        if not self.collection or not text.strip():
            return

        if metadata is None:
            metadata = {}
        
        # Ensure basic metadata
        metadata["source"] = source
        metadata["timestamp"] = metadata.get("timestamp", time.time())
        
        try:
            # ChromaDB requires unique IDs. We'll generate one based on time and hash.
            doc_id = f"{source}_{int(time.time()*1000)}"
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.debug(f"Added memory: {doc_id}")
        except Exception as e:
            logger.error(f"Error adding memory: {e}")

    def query_memory(self, query_text: str, n_results: int = 5, filter_metadata: Optional[Dict] = None) -> List[str]:
        """
        Search for relevant memories.
        
        Args:
            query_text: The query to embed and search for.
            n_results: Number of results to return.
            filter_metadata: Optional filter for metadata (e.g., {"source": "screen"}).
            
        Returns:
            List of relevant text chunks.
        """
        if not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata
            )
            
            # Flatten results (results['documents'] is a list of lists)
            if results and results['documents']:
                return results['documents'][0]
            return []
        except Exception as e:
            logger.error(f"Error querying memory: {e}")
            return []

