import os
import time
from typing import Dict, List, Optional

import chromadb

from app.core import get_logger

logger = get_logger(__name__)

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
        """Add text to vector store and prune if needed."""
        if not self.collection or not text.strip():
            return

        metadata = metadata or {}
        metadata.update({"source": source, "timestamp": metadata.get("timestamp", time.time())})
        
        try:
            doc_id = f"{source}_{int(time.time()*1000)}"
            self.collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
            logger.debug(f"Added memory: {doc_id}")
            
            if self.collection.count() > 10000:
                self._prune_oldest()
        except Exception as e:
            logger.error(f"Error adding memory: {e}")

    def _prune_oldest(self, keep=5000):
        """Keep only the most recent memories."""
        try:
            ids = self.collection.get(include=[])['ids']
            if len(ids) > keep:
                # IDs are timestamp-prefixed, so sorting works roughly (or we parse them)
                # Actually our IDs are {source}_{timestamp}, so string sort might fail for diff sources/lengths
                # Better to rely on metadata if possible, but get() with where is slower.
                # Let's parse the timestamp from the ID for reliable sorting.
                sorted_ids = sorted(ids, key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
                to_delete = sorted_ids[:len(ids) - keep]
                self.collection.delete(ids=to_delete)
                logger.info(f"Pruned {len(to_delete)} old memories")
        except Exception as e:
            logger.error(f"Pruning failed: {e}")


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

