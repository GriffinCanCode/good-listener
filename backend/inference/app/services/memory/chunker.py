"""Semantic chunker for memory storage using embedding similarity."""

import re
from dataclasses import dataclass, field

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core import get_logger

logger = get_logger(__name__)

# Sentence boundary pattern (handles ., !, ?, and common abbreviations)
_SENT_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$')
# Minimum chars for valid sentence
_MIN_SENT_LEN = 10


@dataclass(slots=True)
class ChunkResult:
    """Result of semantic chunking."""
    chunks: list[str]
    boundaries: list[int] = field(default_factory=list)  # Sentence indices where splits occurred


class SemanticChunker:
    """Chunks text by detecting semantic breakpoints via embedding similarity."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 50,
        max_chunk_size: int = 500,
    ):
        self.threshold = similarity_threshold
        self.min_size = min_chunk_size
        self.max_size = max_chunk_size
        self._model: SentenceTransformer | None = None
        self._model_name = model_name

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
            logger.info(f"Loaded chunker model: {self._model_name}")
        return self._model

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences, preserving short fragments."""
        # First try sentence boundary splitting
        parts = _SENT_PATTERN.split(text.strip())
        sentences = [s.strip() for s in parts if s.strip()]

        # If no splits found, split by newlines as fallback
        if len(sentences) <= 1 and '\n' in text:
            sentences = [s.strip() for s in text.split('\n') if s.strip()]

        return sentences

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _find_breakpoints(self, embeddings: np.ndarray) -> list[int]:
        """Find indices where semantic similarity drops below threshold."""
        if len(embeddings) < 2:
            return []

        breakpoints = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            if sim < self.threshold:
                breakpoints.append(i + 1)

        return breakpoints

    def _merge_sentences(self, sentences: list[str], breakpoints: list[int]) -> list[str]:
        """Merge sentences between breakpoints, respecting size constraints."""
        if not sentences:
            return []
        if not breakpoints:
            return [' '.join(sentences)]

        chunks = []
        start = 0

        for bp in breakpoints + [len(sentences)]:
            chunk_sents = sentences[start:bp]
            chunk_text = ' '.join(chunk_sents)

            # Handle size constraints
            if len(chunk_text) > self.max_size:
                # Split oversized chunk
                current = []
                current_len = 0
                for sent in chunk_sents:
                    if current_len + len(sent) > self.max_size and current:
                        chunks.append(' '.join(current))
                        current = [sent]
                        current_len = len(sent)
                    else:
                        current.append(sent)
                        current_len += len(sent) + 1
                if current:
                    chunks.append(' '.join(current))
            elif len(chunk_text) >= self.min_size:
                chunks.append(chunk_text)
            elif chunks:
                # Merge undersized with previous
                chunks[-1] = chunks[-1] + ' ' + chunk_text
            else:
                chunks.append(chunk_text)

            start = bp

        return [c.strip() for c in chunks if c.strip()]

    def chunk(self, text: str) -> ChunkResult:
        """
        Chunk text by semantic similarity boundaries.

        Returns ChunkResult with semantic chunks and boundary indices.
        """
        if not text or len(text.strip()) < _MIN_SENT_LEN:
            return ChunkResult(chunks=[text.strip()] if text.strip() else [])

        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return ChunkResult(chunks=sentences)

        # Compute embeddings for all sentences at once (batched)
        embeddings = self.model.encode(sentences, convert_to_numpy=True, show_progress_bar=False)

        # Find semantic breakpoints
        breakpoints = self._find_breakpoints(embeddings)

        # Merge sentences between breakpoints
        chunks = self._merge_sentences(sentences, breakpoints)

        return ChunkResult(chunks=chunks, boundaries=breakpoints)

    def chunk_batch(self, texts: list[str], merge_related: bool = True) -> list[str]:
        """
        Chunk a batch of texts, optionally merging semantically related items.

        When merge_related=True, consecutive texts with high similarity are
        combined before chunking - ideal for transcript lines that may be
        fragments of the same thought.
        """
        if not texts:
            return []

        # Filter empty texts
        valid = [(i, t.strip()) for i, t in enumerate(texts) if t.strip()]
        if not valid:
            return []

        if len(valid) == 1:
            return self.chunk(valid[0][1]).chunks

        if merge_related:
            # Merge related texts first, then chunk
            _, texts_only = zip(*valid)
            merged = self._merge_related_texts(list(texts_only))
            result = []
            for text in merged:
                result.extend(self.chunk(text).chunks)
            return result
        else:
            # Chunk each text independently
            result = []
            for _, text in valid:
                result.extend(self.chunk(text).chunks)
            return result

    def _merge_related_texts(self, texts: list[str]) -> list[str]:
        """Merge consecutive texts that are semantically related."""
        if len(texts) <= 1:
            return texts

        # Compute embeddings
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        # Find groups of related texts
        merged = []
        current_group = [texts[0]]

        for i in range(1, len(texts)):
            sim = self._cosine_similarity(embeddings[i - 1], embeddings[i])
            if sim >= self.threshold:
                current_group.append(texts[i])
            else:
                merged.append(' '.join(current_group))
                current_group = [texts[i]]

        if current_group:
            merged.append(' '.join(current_group))

        return merged


# Module-level singleton for reuse
_chunker: SemanticChunker | None = None


def get_chunker(
    similarity_threshold: float = 0.5,
    min_chunk_size: int = 50,
    max_chunk_size: int = 500,
) -> SemanticChunker:
    """Get or create the semantic chunker singleton."""
    global _chunker
    if _chunker is None:
        _chunker = SemanticChunker(
            similarity_threshold=similarity_threshold,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
        )
    return _chunker

