import os
import time
from typing import Dict, List, Optional, Tuple

import chromadb

from app.core import get_logger

logger = get_logger(__name__)


class MemoryService:
    # Weights for importance scoring
    RECENCY_WEIGHT = 0.25
    ACCESS_WEIGHT = 0.50
    UNIQUENESS_WEIGHT = 0.25
    
    # Thresholds
    SIMILARITY_THRESHOLD = 0.92  # Duplicates
    CLUSTER_THRESHOLD = 0.75    # Semantic cluster membership
    PROTECTED_ACCESS_COUNT = 5  # Memories with >= this access count are protected

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
        metadata.update({
            "source": source,
            "timestamp": metadata.get("timestamp", time.time()),
            "access_count": 0
        })
        
        try:
            doc_id = f"{source}_{int(time.time()*1000)}"
            self.collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
            logger.debug(f"Added memory: {doc_id}")
            
            if self.collection.count() > 10000:
                self._prune_smart()
        except Exception as e:
            logger.error(f"Error adding memory: {e}")

    def _compute_importance(
        self, timestamp: float, access_count: int, uniqueness: float,
        now: float, max_age: float, max_access: int
    ) -> Tuple[float, bool]:
        """Compute importance score combining recency, access frequency, and semantic uniqueness.
        
        Returns (score, is_protected) where protected memories are never pruned.
        """
        # Protected status: frequently-queried memories survive regardless of age
        is_protected = access_count >= self.PROTECTED_ACCESS_COUNT
        
        age = now - timestamp
        recency_score = 1.0 - (age / max_age) if max_age > 0 else 1.0
        access_score = access_count / max_access if max_access > 0 else 0.0
        
        score = (
            self.RECENCY_WEIGHT * recency_score +
            self.ACCESS_WEIGHT * access_score +
            self.UNIQUENESS_WEIGHT * uniqueness
        )
        return score, is_protected

    def _compute_uniqueness_scores(self, ids: List[str], sample_size: int = 1000) -> Dict[str, float]:
        """Compute semantic uniqueness scores via clustering.
        
        Memories that are cluster representatives (less similar to others) get higher scores.
        """
        uniqueness = {id_: 1.0 for id_ in ids}  # Default: fully unique
        if len(ids) < 2:
            return uniqueness
        
        try:
            # Sample for efficiency on large collections
            sample_ids = ids[:sample_size] if len(ids) > sample_size else ids
            data = self.collection.get(ids=sample_ids, include=['documents', 'embeddings'])
            docs = data.get('documents', [])
            if not docs:
                return uniqueness
            
            # Query each doc's neighbors to measure semantic density
            for i, (id_, doc) in enumerate(zip(sample_ids, docs)):
                if not doc:
                    continue
                results = self.collection.query(
                    query_texts=[doc], n_results=min(10, len(ids)),
                    include=['distances']
                )
                if not results.get('distances') or not results['distances'][0]:
                    continue
                
                # Avg distance to neighbors (excluding self at distance 0)
                distances = [d for d in results['distances'][0] if d > 0.001]
                if distances:
                    avg_dist = sum(distances) / len(distances)
                    # Higher avg distance = more unique (less similar to others)
                    uniqueness[id_] = min(1.0, avg_dist / (1.0 - self.CLUSTER_THRESHOLD))
        except Exception as e:
            logger.debug(f"Uniqueness computation failed: {e}")
        
        return uniqueness

    def _prune_smart(self, keep: int = 5000):
        """Importance-aware pruning: preserves frequently-accessed and semantically unique memories."""
        try:
            data = self.collection.get(include=['metadatas'])
            ids, metadatas = data['ids'], data['metadatas']
            if len(ids) <= keep:
                return

            now = time.time()
            timestamps = [m.get('timestamp', 0) for m in metadatas]
            access_counts = [m.get('access_count', 0) for m in metadatas]
            max_age = now - min(timestamps) if timestamps else 1.0
            max_access = max(access_counts) if access_counts else 1
            
            # Compute semantic uniqueness for diverse preservation
            uniqueness = self._compute_uniqueness_scores(ids)

            # Score each memory; track protected status
            scored = []
            for id_, ts, ac in zip(ids, timestamps, access_counts):
                uniq = uniqueness.get(id_, 1.0)
                score, protected = self._compute_importance(ts, ac, uniq, now, max_age, max_access)
                scored.append((id_, score, protected))
            
            # Separate protected from pruneable
            protected_ids = {s[0] for s in scored if s[2]}
            pruneable = [(id_, score) for id_, score, prot in scored if not prot]
            
            # Sort pruneable by score ascending (lowest importance first)
            pruneable.sort(key=lambda x: x[1])
            
            # Calculate how many to delete, respecting protected count
            target_delete = len(ids) - keep
            to_delete = [id_ for id_, _ in pruneable[:target_delete]]
            
            if to_delete:
                self.collection.delete(ids=to_delete)
                logger.info(f"Pruned {len(to_delete)} memories ({len(protected_ids)} protected)")
        except Exception as e:
            logger.error(f"Smart pruning failed: {e}")

    def _prune_duplicates(self, sample_size: int = 500, threshold: float = None):
        """Remove semantically redundant memories, keeping the more important one."""
        threshold = threshold or self.SIMILARITY_THRESHOLD
        try:
            data = self.collection.get(include=['documents', 'metadatas'])
            ids, docs, metas = data['ids'], data['documents'], data['metadatas']
            if len(ids) < 2:
                return

            # Sample recent memories to check for duplicates
            now = time.time()
            indexed = list(zip(ids, docs, metas))
            indexed.sort(key=lambda x: x[2].get('timestamp', 0), reverse=True)
            sample = indexed[:sample_size]

            to_delete = set()
            for i, (id1, doc1, meta1) in enumerate(sample):
                if id1 in to_delete:
                    continue
                # Query for similar documents
                results = self.collection.query(
                    query_texts=[doc1], n_results=5, include=['metadatas', 'distances']
                )
                if not results['ids'] or not results['ids'][0]:
                    continue
                
                for j, (rid, dist) in enumerate(zip(results['ids'][0], results['distances'][0])):
                    if rid == id1 or rid in to_delete:
                        continue
                    similarity = 1.0 - dist  # cosine distance to similarity
                    if similarity >= threshold:
                        # Keep the one with higher access count, or more recent if tied
                        rmeta = results['metadatas'][0][j] if results['metadatas'] else {}
                        ac1, ac2 = meta1.get('access_count', 0), rmeta.get('access_count', 0)
                        ts1, ts2 = meta1.get('timestamp', 0), rmeta.get('timestamp', 0)
                        victim = rid if (ac1 > ac2 or (ac1 == ac2 and ts1 >= ts2)) else id1
                        to_delete.add(victim)

            if to_delete:
                self.collection.delete(ids=list(to_delete))
                logger.info(f"Deduplicated {len(to_delete)} redundant memories")
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")


    def query_memory(self, query_text: str, n_results: int = 5, filter_metadata: Optional[Dict] = None) -> List[str]:
        """
        Search for relevant memories and increment their access counts.
        
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
                where=filter_metadata,
                include=['documents', 'metadatas']
            )
            
            if not results or not results['documents']:
                return []
            
            # Increment access counts for retrieved memories
            self._increment_access_counts(results['ids'][0], results['metadatas'][0])
            
            return results['documents'][0]
        except Exception as e:
            logger.error(f"Error querying memory: {e}")
            return []

    def _increment_access_counts(self, ids: List[str], metadatas: List[Dict]):
        """Increment access_count for retrieved memories."""
        try:
            for id_, meta in zip(ids, metadatas):
                updated = {**meta, 'access_count': meta.get('access_count', 0) + 1}
                self.collection.update(ids=[id_], metadatas=[updated])
        except Exception as e:
            logger.debug(f"Failed to update access counts: {e}")

