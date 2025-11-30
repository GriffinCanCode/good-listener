import threading
import time
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue

import chromadb

from app.core import get_logger
from app.services.constants import (
    DEDUP_NEIGHBOR_COUNT,
    DEDUP_SAMPLE_SIZE,
    MEMORY_PRUNE_KEEP,
    MEMORY_PRUNE_THRESHOLD,
    MEMORY_QUERY_DEFAULT_RESULTS,
    POOL_ACQUIRE_TIMEOUT,
    POOL_SIZE_DEFAULT,
    UNIQUENESS_DISTANCE_EPSILON,
    UNIQUENESS_NEIGHBOR_COUNT,
    UNIQUENESS_SAMPLE_SIZE,
)

logger = get_logger(__name__)


class ChromaPool:
    """Thread-safe connection pool for ChromaDB clients."""

    def __init__(self, persistence_path: str, pool_size: int = POOL_SIZE_DEFAULT, collection_name: str = "user_context"):
        self._path, self._pool_size, self._collection_name = persistence_path, pool_size, collection_name
        self._pool: Queue[tuple[chromadb.PersistentClient, chromadb.Collection]] = Queue(maxsize=pool_size)
        self._lock, self._initialized = threading.Lock(), False

    def _create_client(self) -> tuple[chromadb.PersistentClient, chromadb.Collection]:
        client = chromadb.PersistentClient(path=self._path)
        return client, client.get_or_create_collection(name=self._collection_name, metadata={"hnsw:space": "cosine"})

    def initialize(self) -> bool:
        """Lazy-initialize the pool with connections."""
        if self._initialized:
            return True
        with self._lock:
            if self._initialized:
                return True
            try:
                for _ in range(self._pool_size):
                    self._pool.put(self._create_client())
                self._initialized = True
                logger.info(f"ChromaPool initialized with {self._pool_size} clients")
                return True
            except Exception:
                logger.exception("Failed to initialize ChromaPool")
                return False

    @contextmanager
    def acquire(self, timeout: float = POOL_ACQUIRE_TIMEOUT):
        """Acquire a client/collection pair from the pool."""
        if not self._initialized and not self.initialize():
            yield None, None
            return
        try:
            pair = self._pool.get(timeout=timeout)
            try:
                yield pair
            finally:
                self._pool.put(pair)
        except Empty:
            logger.warning("ChromaPool exhausted, creating ephemeral client")
            yield self._create_client()

    def close(self):
        """Close all pooled connections."""
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break


class MemoryService:
    # Weights for importance scoring
    RECENCY_WEIGHT, ACCESS_WEIGHT, UNIQUENESS_WEIGHT = 0.25, 0.50, 0.25
    # Thresholds
    SIMILARITY_THRESHOLD = 0.92  # Duplicates
    CLUSTER_THRESHOLD = 0.75  # Semantic cluster membership
    PROTECTED_ACCESS_COUNT = 5  # Memories with >= this access count are protected

    def __init__(self, persistence_path: str = "data/chroma_db", pool_size: int = POOL_SIZE_DEFAULT):
        self.persistence_path = persistence_path
        Path(persistence_path).mkdir(parents=True, exist_ok=True)
        self._pool = ChromaPool(persistence_path, pool_size)
        # Legacy attributes for backwards compatibility
        self.client, self.collection = None, None
        if self._pool.initialize():
            with self._pool.acquire() as (client, collection):
                self.client, self.collection = client, collection
            logger.info(f"MemoryService initialized with pool at {self.persistence_path}")

    def add_memory(self, text: str, source: str, metadata: dict | None = None) -> str | None:
        """Add text to vector store and prune if needed. Returns doc_id on success."""
        if not text.strip():
            return None
        m = metadata or {}
        meta = {**m, "source": source, "timestamp": m.get("timestamp", time.time()), "access_count": 0}
        doc_id = f"{source}_{int(time.time() * 1000)}_{threading.get_ident()}"
        try:
            with self._pool.acquire() as (_, collection):
                if not collection:
                    return None
                collection.add(documents=[text], metadatas=[meta], ids=[doc_id])
                logger.debug(f"Added memory: {doc_id}")
                if collection.count() > MEMORY_PRUNE_THRESHOLD:
                    self._prune_smart()
            return doc_id
        except Exception:
            logger.exception("Error adding memory")
            return None

    def add_memories_batch(self, items: list[tuple[str, str, dict | None]]) -> list[str]:
        """Batch add multiple memories. Items are (text, source, metadata) tuples."""
        if not items:
            return []
        now, tid, ms = time.time(), threading.get_ident(), int(time.time() * 1000)
        entries = [(text, {**(m := meta or {}), "source": src, "timestamp": m.get("timestamp", now), "access_count": 0},
                    f"{src}_{ms}_{tid}_{i}") for i, (text, src, meta) in enumerate(items) if text.strip()]
        if not entries:
            return []
        docs, metas, ids = zip(*entries)
        try:
            with self._pool.acquire() as (_, collection):
                if not collection:
                    return []
                collection.add(documents=list(docs), metadatas=list(metas), ids=list(ids))
                logger.debug(f"Batch added {len(ids)} memories")
                if collection.count() > MEMORY_PRUNE_THRESHOLD:
                    self._prune_smart()
            return list(ids)
        except Exception:
            logger.exception("Error batch adding memories")
            return []

    def _compute_importance(
        self, timestamp: float, access_count: int, uniqueness: float, now: float, max_age: float, max_access: int
    ) -> tuple[float, bool]:
        """Compute importance score (recency + access + uniqueness). Returns (score, is_protected)."""
        recency = 1.0 - ((now - timestamp) / max_age) if max_age > 0 else 1.0
        access = access_count / max_access if max_access > 0 else 0.0
        score = self.RECENCY_WEIGHT * recency + self.ACCESS_WEIGHT * access + self.UNIQUENESS_WEIGHT * uniqueness
        return score, access_count >= self.PROTECTED_ACCESS_COUNT

    def _compute_uniqueness_scores(self, ids: list[str], collection, sample_size: int = UNIQUENESS_SAMPLE_SIZE) -> dict[str, float]:
        """Compute semantic uniqueness via clustering. Cluster representatives (less similar) get higher scores."""
        uniq = dict.fromkeys(ids, 1.0)  # Default: fully unique
        if len(ids) < 2:
            return uniq
        try:
            sids = ids[:sample_size] if len(ids) > sample_size else ids
            if not (docs := collection.get(ids=sids, include=["documents", "embeddings"]).get("documents", [])):
                return uniq
            # Query each doc's neighbors to measure semantic density
            for id_, doc in zip(sids, docs, strict=False):
                if not doc:
                    continue
                res = collection.query(query_texts=[doc], n_results=min(UNIQUENESS_NEIGHBOR_COUNT, len(ids)), include=["distances"])
                if not (dists := res.get("distances", [[]])[0]):
                    continue
                # Avg distance to neighbors (excluding self at distance 0)
                if distances := [d for d in dists if d > UNIQUENESS_DISTANCE_EPSILON]:
                    uniq[id_] = min(1.0, (sum(distances) / len(distances)) / (1.0 - self.CLUSTER_THRESHOLD))
        except Exception as e:
            logger.debug(f"Uniqueness computation failed: {e}")
        return uniq

    def _prune_smart(self, keep: int = MEMORY_PRUNE_KEEP):
        """Importance-aware pruning: preserves frequently-accessed and semantically unique memories."""
        try:
            with self._pool.acquire() as (_, collection):
                if not collection:
                    return
                data = collection.get(include=["metadatas"])
                ids, metas = data["ids"], data["metadatas"]
                if len(ids) <= keep:
                    return
                now = time.time()
                ts_list = [m.get("timestamp", 0) for m in metas]
                ac_list = [m.get("access_count", 0) for m in metas]
                max_age, max_access = (now - min(ts_list)) if ts_list else 1.0, max(ac_list, default=1)
                uniq = self._compute_uniqueness_scores(ids, collection)
                # Score each memory; separate protected from pruneable
                scored = [(id_, *self._compute_importance(ts, ac, uniq.get(id_, 1.0), now, max_age, max_access))
                          for id_, ts, ac in zip(ids, ts_list, ac_list, strict=True)]
                protected = sum(1 for _, _, p in scored if p)
                pruneable = sorted(((id_, sc) for id_, sc, p in scored if not p), key=lambda x: x[1])
                if to_delete := [id_ for id_, _ in pruneable[:len(ids) - keep]]:
                    collection.delete(ids=to_delete)
                    logger.info(f"Pruned {len(to_delete)} memories ({protected} protected)")
        except Exception:
            logger.exception("Smart pruning failed")

    def _prune_duplicates(self, sample_size: int = DEDUP_SAMPLE_SIZE, threshold: float | None = None):
        """Remove semantically redundant memories, keeping the more important one."""
        thresh = threshold or self.SIMILARITY_THRESHOLD
        try:
            with self._pool.acquire() as (_, collection):
                if not collection:
                    return
                data = collection.get(include=["documents", "metadatas"])
                ids, docs, metas = data["ids"], data["documents"], data["metadatas"]
                if len(ids) < 2:
                    return
                # Sample recent memories to check for duplicates
                sample = sorted(zip(ids, docs, metas, strict=True), key=lambda x: x[2].get("timestamp", 0), reverse=True)[:sample_size]
                to_del: set[str] = set()
                for id1, doc1, m1 in sample:
                    if id1 in to_del:
                        continue
                    res = collection.query(query_texts=[doc1], n_results=DEDUP_NEIGHBOR_COUNT, include=["metadatas", "distances"])
                    if not res["ids"] or not res["ids"][0]:
                        continue
                    for idx, (rid, dist) in enumerate(zip(res["ids"][0], res["distances"][0], strict=True)):
                        if rid == id1 or rid in to_del or (1.0 - dist) < thresh:
                            continue
                        # Keep the one with higher access count, or more recent if tied
                        rm = res["metadatas"][0][idx] if res["metadatas"] else {}
                        ac1, ac2 = m1.get("access_count", 0), rm.get("access_count", 0)
                        ts1, ts2 = m1.get("timestamp", 0), rm.get("timestamp", 0)
                        to_del.add(rid if (ac1 > ac2 or (ac1 == ac2 and ts1 >= ts2)) else id1)
                if to_del:
                    collection.delete(ids=list(to_del))
                    logger.info(f"Deduplicated {len(to_del)} redundant memories")
        except Exception:
            logger.exception("Deduplication failed")

    def query_memory(self, query_text: str, n_results: int = MEMORY_QUERY_DEFAULT_RESULTS, filter_metadata: dict | None = None) -> list[str]:
        """Search for relevant memories and increment their access counts."""
        try:
            with self._pool.acquire() as (_, collection):
                if not collection:
                    return []
                res = collection.query(query_texts=[query_text], n_results=n_results, where=filter_metadata, include=["documents", "metadatas"])
                if not res or not res["documents"]:
                    return []
                # Increment access counts for retrieved memories
                try:
                    for id_, m in zip(res["ids"][0], res["metadatas"][0], strict=True):
                        collection.update(ids=[id_], metadatas=[{**m, "access_count": m.get("access_count", 0) + 1}])
                except Exception:
                    logger.debug("Failed to update access counts", exc_info=True)
                return res["documents"][0]
        except Exception:
            logger.exception("Error querying memory")
            return []
