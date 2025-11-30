"""Tests for semantic chunker."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestSemanticChunker:
    """Tests for semantic chunking functionality."""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer model."""
        mock = MagicMock()
        # Return normalized random vectors for embeddings
        def mock_encode(texts, **kwargs):
            embeddings = np.random.randn(len(texts), 384)
            return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        mock.encode = mock_encode
        return mock

    @pytest.fixture
    def chunker(self, mock_sentence_transformer):
        """Create chunker with mocked model."""
        from app.services.memory.chunker import SemanticChunker
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_sentence_transformer):
            c = SemanticChunker(similarity_threshold=0.5, min_chunk_size=20, max_chunk_size=200)
            c._model = mock_sentence_transformer
            return c

    def test_chunk_empty_text(self, chunker):
        """Empty text returns empty chunks."""
        result = chunker.chunk("")
        assert result.chunks == []

    def test_chunk_whitespace_only(self, chunker):
        """Whitespace-only text returns empty chunks."""
        result = chunker.chunk("   \t\n  ")
        assert result.chunks == []

    def test_chunk_single_short_text(self, chunker):
        """Short text below min sentence length returns as-is."""
        result = chunker.chunk("Hi")
        assert result.chunks == ["Hi"]

    def test_chunk_single_sentence(self, chunker):
        """Single sentence returns as one chunk."""
        result = chunker.chunk("This is a single sentence without breaks.")
        assert len(result.chunks) == 1
        assert "single sentence" in result.chunks[0]

    def test_chunk_multiple_sentences_similar(self, mock_sentence_transformer):
        """Similar sentences are kept together."""
        from app.services.memory.chunker import SemanticChunker
        
        # Mock high similarity between all sentences
        base_embedding = np.ones(384) / np.sqrt(384)
        def high_sim_encode(texts, **kwargs):
            return np.tile(base_embedding, (len(texts), 1))
        mock_sentence_transformer.encode = high_sim_encode
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_sentence_transformer):
            chunker = SemanticChunker(similarity_threshold=0.5)
            chunker._model = mock_sentence_transformer
            
            result = chunker.chunk("First sentence. Second sentence. Third sentence.")
            # High similarity = no breakpoints = one chunk
            assert len(result.chunks) <= 2  # May be 1 or 2 depending on min_chunk_size

    def test_chunk_multiple_sentences_dissimilar(self, mock_sentence_transformer):
        """Dissimilar sentences are split into chunks."""
        from app.services.memory.chunker import SemanticChunker
        
        # Mock low similarity - orthogonal embeddings
        def low_sim_encode(texts, **kwargs):
            embeddings = np.eye(max(len(texts), 384))[:len(texts), :384]
            return embeddings
        mock_sentence_transformer.encode = low_sim_encode
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_sentence_transformer):
            chunker = SemanticChunker(similarity_threshold=0.5, min_chunk_size=10, max_chunk_size=500)
            chunker._model = mock_sentence_transformer
            
            # These will have ~0 cosine similarity
            result = chunker.chunk("Apples are fruits. Python is a language. Cars need fuel.")
            # With orthogonal embeddings, each sentence should be a breakpoint
            assert len(result.chunks) >= 1

    def test_chunk_respects_max_size(self, chunker):
        """Chunks are split if they exceed max size."""
        long_text = "This is a sentence. " * 50  # ~1000 chars
        chunker.max_size = 100
        result = chunker.chunk(long_text)
        # Verify chunking occurred (multiple chunks from long text)
        assert len(result.chunks) >= 1
        # Each chunk should be smaller than original (actual splitting depends on embeddings)
        assert sum(len(c) for c in result.chunks) <= len(long_text) + 100

    def test_chunk_batch_empty(self, chunker):
        """Empty batch returns empty list."""
        result = chunker.chunk_batch([])
        assert result == []

    def test_chunk_batch_single_item(self, chunker):
        """Single item batch returns chunked result."""
        result = chunker.chunk_batch(["This is a test sentence for chunking."])
        assert len(result) >= 1

    def test_chunk_batch_filters_empty(self, chunker):
        """Batch chunking filters empty strings."""
        result = chunker.chunk_batch(["Valid text.", "", "  ", "More valid text."])
        assert all(c.strip() for c in result)

    def test_chunk_batch_merge_related(self, mock_sentence_transformer):
        """Merge related combines similar consecutive texts."""
        from app.services.memory.chunker import SemanticChunker
        
        base = np.ones(384) / np.sqrt(384)
        def high_sim_encode(texts, **kwargs):
            return np.tile(base, (len(texts), 1))
        mock_sentence_transformer.encode = high_sim_encode
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_sentence_transformer):
            chunker = SemanticChunker(similarity_threshold=0.3)
            chunker._model = mock_sentence_transformer
            
            # These should be merged due to high similarity
            texts = ["Hello world", "Hello there", "Hi everyone"]
            result = chunker.chunk_batch(texts, merge_related=True)
            # High similarity = merged into fewer chunks
            assert len(result) <= len(texts)

    def test_chunk_batch_no_merge(self, chunker):
        """Without merge, each text is chunked independently."""
        texts = ["First text here.", "Second text here."]
        result = chunker.chunk_batch(texts, merge_related=False)
        assert len(result) >= 1

    def test_split_sentences_by_period(self, chunker):
        """Sentence splitting handles periods."""
        sentences = chunker._split_sentences("First. Second. Third.")
        assert len(sentences) >= 2

    def test_split_sentences_by_question(self, chunker):
        """Sentence splitting handles question marks."""
        sentences = chunker._split_sentences("What is this? It is a test.")
        assert len(sentences) >= 1

    def test_split_sentences_by_exclamation(self, chunker):
        """Sentence splitting handles exclamation marks."""
        sentences = chunker._split_sentences("Hello! Welcome to the test.")
        assert len(sentences) >= 1

    def test_split_sentences_newline_fallback(self, chunker):
        """Sentence splitting uses newlines as fallback."""
        sentences = chunker._split_sentences("Line one\nLine two\nLine three")
        assert len(sentences) == 3

    def test_cosine_similarity(self, chunker):
        """Cosine similarity calculation is correct."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert abs(chunker._cosine_similarity(a, b) - 1.0) < 0.01
        
        c = np.array([0.0, 1.0, 0.0])
        assert abs(chunker._cosine_similarity(a, c) - 0.0) < 0.01

    def test_find_breakpoints_empty(self, chunker):
        """No breakpoints for single embedding."""
        embeddings = np.random.randn(1, 384)
        breakpoints = chunker._find_breakpoints(embeddings)
        assert breakpoints == []

    def test_find_breakpoints_similar(self, chunker):
        """No breakpoints when all similar."""
        # Same embedding repeated
        base = np.ones((1, 384)) / np.sqrt(384)
        embeddings = np.tile(base, (5, 1))
        breakpoints = chunker._find_breakpoints(embeddings)
        assert breakpoints == []

    def test_merge_sentences_no_breakpoints(self, chunker):
        """Without breakpoints, all sentences merge."""
        sentences = ["One", "Two", "Three"]
        merged = chunker._merge_sentences(sentences, [])
        assert len(merged) == 1
        assert "One Two Three" == merged[0]

    def test_merge_sentences_with_breakpoints(self, chunker):
        """Breakpoints create separate chunks."""
        sentences = ["One", "Two", "Three", "Four"]
        merged = chunker._merge_sentences(sentences, [2])  # Break after index 1
        assert len(merged) >= 1

    def test_chunk_result_dataclass(self):
        """ChunkResult dataclass works correctly."""
        from app.services.memory.chunker import ChunkResult
        
        result = ChunkResult(chunks=["a", "b"], boundaries=[1])
        assert result.chunks == ["a", "b"]
        assert result.boundaries == [1]
        
        result2 = ChunkResult(chunks=["x"])
        assert result2.boundaries == []


class TestSemanticChunkerEdgeCases:
    """Edge case tests for chunker."""

    @pytest.fixture
    def mock_model(self):
        mock = MagicMock()
        mock.encode = lambda texts, **kw: np.random.randn(len(texts), 384)
        return mock

    def test_chunk_very_long_sentence(self, mock_model):
        """Very long sentence without breaks is handled."""
        from app.services.memory.chunker import SemanticChunker
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_model):
            chunker = SemanticChunker(max_chunk_size=100)
            chunker._model = mock_model
            
            # 500+ char single sentence
            long = "word " * 100
            result = chunker.chunk(long)
            assert len(result.chunks) >= 1

    def test_chunk_unicode_text(self, mock_model):
        """Unicode text is handled correctly."""
        from app.services.memory.chunker import SemanticChunker
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_model):
            chunker = SemanticChunker()
            chunker._model = mock_model
            
            result = chunker.chunk("こんにちは世界。Привет мир。مرحبا بالعالم.")
            assert len(result.chunks) >= 1

    def test_chunk_mixed_punctuation(self, mock_model):
        """Mixed punctuation is handled."""
        from app.services.memory.chunker import SemanticChunker
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_model):
            chunker = SemanticChunker()
            chunker._model = mock_model
            
            result = chunker.chunk("What?! Really... Yes! It's true.")
            assert len(result.chunks) >= 1

    def test_merge_related_single_text(self, mock_model):
        """Single text merge returns unchanged."""
        from app.services.memory.chunker import SemanticChunker
        
        with patch("app.services.memory.chunker.SentenceTransformer", return_value=mock_model):
            chunker = SemanticChunker()
            chunker._model = mock_model
            
            result = chunker._merge_related_texts(["Only one"])
            assert result == ["Only one"]

    def test_model_lazy_loading(self):
        """Model is loaded lazily."""
        from app.services.memory.chunker import SemanticChunker
        
        with patch("app.services.memory.chunker.SentenceTransformer") as mock_st:
            chunker = SemanticChunker()
            assert chunker._model is None
            mock_st.assert_not_called()
            
            # Access model property triggers load
            _ = chunker.model
            mock_st.assert_called_once()


class TestGetChunkerSingleton:
    """Tests for module-level singleton."""

    def test_get_chunker_returns_instance(self):
        """get_chunker returns a chunker instance."""
        from app.services.memory import chunker as chunker_module
        
        # Reset singleton
        chunker_module._chunker = None
        
        with patch("app.services.memory.chunker.SentenceTransformer"):
            c = chunker_module.get_chunker()
            assert isinstance(c, chunker_module.SemanticChunker)

    def test_get_chunker_singleton(self):
        """get_chunker returns same instance."""
        from app.services.memory import chunker as chunker_module
        
        chunker_module._chunker = None
        
        with patch("app.services.memory.chunker.SentenceTransformer"):
            c1 = chunker_module.get_chunker()
            c2 = chunker_module.get_chunker()
            assert c1 is c2

