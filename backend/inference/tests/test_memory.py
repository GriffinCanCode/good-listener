"""Tests for MemoryService."""

import time
from unittest.mock import patch


class TestMemoryService:
    """Tests for vector memory storage."""

    def test_init_success(self, mock_chromadb):
        """MemoryService initializes ChromaDB client."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test_chroma")

            assert service.client is not None
            assert service.collection is not None

    def test_init_failure(self):
        """MemoryService handles init failure gracefully."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient", side_effect=Exception("Failed")):
            with patch("os.path.exists", return_value=True):
                service = MemoryService()

                assert service.client is None
                assert service.collection is None

    def test_add_memory_success(self, mock_chromadb):
        """add_memory stores text in collection."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("Test memory content", "audio")

            mock_chromadb.add.assert_called_once()
            call_args = mock_chromadb.add.call_args
            assert call_args.kwargs["documents"] == ["Test memory content"]
            assert call_args.kwargs["metadatas"][0]["source"] == "audio"

    def test_add_memory_empty_text(self, mock_chromadb):
        """add_memory skips empty text."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("   ", "audio")

            mock_chromadb.add.assert_not_called()

    def test_add_memory_no_collection(self):
        """add_memory handles missing collection."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient", side_effect=Exception("Failed")):
            with patch("os.path.exists", return_value=True):
                service = MemoryService()
                # Should not raise
                service.add_memory("Test", "audio")

    def test_add_memory_with_metadata(self, mock_chromadb):
        """add_memory includes custom metadata."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            custom_meta = {"topic": "code", "language": "python"}
            service.add_memory("Code snippet", "screen", metadata=custom_meta)

            call_args = mock_chromadb.add.call_args
            metadata = call_args.kwargs["metadatas"][0]
            assert metadata["topic"] == "code"
            assert metadata["language"] == "python"
            assert metadata["source"] == "screen"

    def test_add_memory_triggers_prune(self, mock_chromadb):
        """add_memory prunes when count exceeds threshold."""
        from app.services.memory import MemoryService

        mock_chromadb.count.return_value = 10001  # Over threshold
        # Include metadatas for smart pruning
        mock_chromadb.get.return_value = {
            "ids": [f"audio_{i}" for i in range(10001)],
            "metadatas": [{"timestamp": i, "access_count": 0} for i in range(10001)],
            "documents": [],
        }
        # Mock uniqueness query
        mock_chromadb.query.return_value = {"ids": [[]], "distances": [[]]}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("Test", "audio")

            mock_chromadb.delete.assert_called_once()

    def test_query_memory_success(self, mock_chromadb):
        """query_memory returns matching documents."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("coding help", n_results=3)

            mock_chromadb.query.assert_called_once()
            assert results == ["Relevant memory 1", "Relevant memory 2"]

    def test_query_memory_with_filter(self, mock_chromadb):
        """query_memory passes metadata filter."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", filter_metadata={"source": "screen"})

            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs["where"] == {"source": "screen"}

    def test_query_memory_no_collection(self):
        """query_memory returns empty list when no collection."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient", side_effect=Exception("Failed")):
            with patch("os.path.exists", return_value=True):
                service = MemoryService()
                results = service.query_memory("test")

                assert results == []

    def test_query_memory_empty_results(self, mock_chromadb):
        """query_memory handles empty results."""
        from app.services.memory import MemoryService

        mock_chromadb.query.return_value = {"documents": [[]]}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("nonexistent")

            assert results == []

    def test_query_memory_exception(self, mock_chromadb):
        """query_memory handles exceptions gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.query.side_effect = Exception("Query failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("test")

            assert results == []

    def test_prune_smart_removes_low_importance(self, mock_chromadb):
        """_prune_smart removes low-importance memories first."""
        from app.services.memory import MemoryService

        # Create memories with varying importance
        ids = [f"audio_{i}" for i in range(6000)]
        metadatas = [{"timestamp": i, "access_count": i % 10} for i in range(6000)]
        mock_chromadb.get.return_value = {"ids": ids, "metadatas": metadatas, "documents": []}
        # Mock uniqueness query (uniform uniqueness for simplicity)
        mock_chromadb.query.return_value = {"ids": [[]], "distances": [[]]}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_smart(keep=5000)

            mock_chromadb.delete.assert_called_once()
            deleted_ids = mock_chromadb.delete.call_args.kwargs["ids"]
            # Some may be protected due to access_count >= 5, so deletion count may vary
            assert len(deleted_ids) >= 500  # At least some pruned

    def test_prune_smart_preserves_high_access(self, mock_chromadb):
        """_prune_smart preserves frequently accessed memories."""
        from app.services.memory import MemoryService

        # Old but frequently accessed should survive (and be protected)
        ids = ["old_high_access", "new_low_access"]
        metadatas = [
            {"timestamp": 1000, "access_count": 100},  # Old but high access (protected)
            {"timestamp": 9999, "access_count": 0},  # New but never accessed
        ]
        mock_chromadb.get.return_value = {"ids": ids, "metadatas": metadatas}
        # Mock uniqueness query
        mock_chromadb.query.return_value = {"ids": [["old_high_access"]], "distances": [[0.0, 0.3]]}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_smart(keep=1)

            deleted = mock_chromadb.delete.call_args.kwargs["ids"]
            # The new but low-access memory should be pruned
            assert "new_low_access" in deleted
            assert "old_high_access" not in deleted

    def test_prune_smart_protects_frequently_queried(self, mock_chromadb):
        """_prune_smart protects memories above PROTECTED_ACCESS_COUNT threshold."""
        from app.services.memory import MemoryService

        # All have same recency, but different access counts
        ids = ["protected_1", "protected_2", "pruneable"]
        metadatas = [
            {"timestamp": 1000, "access_count": 10},  # Protected
            {"timestamp": 1000, "access_count": 5},  # Protected (at threshold)
            {"timestamp": 9999, "access_count": 4},  # Below threshold, pruneable
        ]
        mock_chromadb.get.return_value = {"ids": ids, "metadatas": metadatas}
        mock_chromadb.query.return_value = {"ids": [[]], "distances": [[]]}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_smart(keep=2)

            deleted = mock_chromadb.delete.call_args.kwargs["ids"]
            assert "pruneable" in deleted
            assert "protected_1" not in deleted
            assert "protected_2" not in deleted

    def test_ensure_data_dir(self):
        """_ensure_data_dir creates directory if missing."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.Path") as mock_path:
            with patch("app.services.memory.service.chromadb.PersistentClient"):
                MemoryService(persistence_path="/tmp/new_dir")
                mock_path.return_value.mkdir.assert_called_with(parents=True, exist_ok=True)


class TestMemoryServiceEdgeCases:
    """Edge case tests for MemoryService."""

    def test_add_memory_whitespace_only(self, mock_chromadb):
        """add_memory skips whitespace-only text."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("\t\n  ", "audio")

            mock_chromadb.add.assert_not_called()

    def test_add_memory_exception_handling(self, mock_chromadb):
        """add_memory handles add exception gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.add.side_effect = Exception("Add failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise
            service.add_memory("Test content", "audio")

    def test_query_memory_with_special_characters(self, mock_chromadb):
        """query_memory handles special characters in query."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("def func(): return {}", n_results=3)

            mock_chromadb.query.assert_called_once()

    def test_query_memory_large_n_results(self, mock_chromadb):
        """query_memory handles large n_results."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", n_results=1000)

            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs["n_results"] == 1000

    def test_add_memory_preserves_custom_timestamp(self, mock_chromadb):
        """add_memory preserves custom timestamp in metadata."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            custom_meta = {"timestamp": 1234567890}
            service.add_memory("Test", "screen", metadata=custom_meta)

            call_args = mock_chromadb.add.call_args
            assert call_args.kwargs["metadatas"][0]["timestamp"] == 1234567890

    def test_prune_smart_no_ids(self, mock_chromadb):
        """_prune_smart handles empty ID list."""
        from app.services.memory import MemoryService

        mock_chromadb.get.return_value = {"ids": [], "metadatas": [], "documents": []}

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_smart(keep=5000)

            mock_chromadb.delete.assert_not_called()

    def test_prune_smart_under_threshold(self, mock_chromadb):
        """_prune_smart skips when under threshold."""
        from app.services.memory import MemoryService

        mock_chromadb.get.return_value = {
            "ids": [f"audio_{i}" for i in range(100)],
            "metadatas": [{"timestamp": i, "access_count": 0} for i in range(100)],
            "documents": [],
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_smart(keep=5000)

            mock_chromadb.delete.assert_not_called()

    def test_prune_smart_exception(self, mock_chromadb):
        """_prune_smart handles exceptions gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.get.side_effect = Exception("Get failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise
            service._prune_smart(keep=5000)


class TestMemoryServiceConcurrency:
    """Tests for concurrent memory operations."""

    def test_add_memory_generates_unique_ids(self, mock_chromadb):
        """add_memory generates unique IDs for concurrent calls."""
        import time

        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")

            service.add_memory("First", "audio")
            time.sleep(0.002)  # Ensure different timestamp
            service.add_memory("Second", "audio")

            calls = mock_chromadb.add.call_args_list
            id1 = calls[0].kwargs["ids"][0]
            id2 = calls[1].kwargs["ids"][0]

            assert id1 != id2

    def test_query_memory_none_filter(self, mock_chromadb):
        """query_memory handles None filter_metadata."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", filter_metadata=None)

            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs["where"] is None


class TestImportanceScoring:
    """Tests for importance-aware memory scoring."""

    def test_compute_importance_high_access(self, mock_chromadb):
        """High access count yields high importance score."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            now = time.time()

            # Old but high access
            score, protected = service._compute_importance(
                timestamp=now - 10000, access_count=100, uniqueness=0.5, now=now, max_age=10000, max_access=100
            )
            # With weights: 0.25*0(recency) + 0.50*1.0(access) + 0.25*0.5(unique) = 0.625
            assert score >= 0.5
            assert protected  # High access = protected

    def test_compute_importance_recent_low_access(self, mock_chromadb):
        """Recent but low access yields moderate importance."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            now = time.time()

            # Very recent, no access
            score, protected = service._compute_importance(
                timestamp=now, access_count=0, uniqueness=1.0, now=now, max_age=10000, max_access=100
            )
            # 0.25*1.0(recency) + 0.50*0(access) + 0.25*1.0(unique) = 0.5
            assert 0.45 <= score <= 0.55
            assert not protected

    def test_compute_importance_balanced(self, mock_chromadb):
        """Moderate recency and access yields high score."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            now = time.time()

            score, protected = service._compute_importance(
                timestamp=now - 5000, access_count=50, uniqueness=0.5, now=now, max_age=10000, max_access=100
            )
            # 0.25*0.5 + 0.50*0.5 + 0.25*0.5 = 0.5
            assert 0.45 <= score <= 0.55

    def test_compute_importance_protected_threshold(self, mock_chromadb):
        """Memories with access_count >= PROTECTED_ACCESS_COUNT are protected."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            now = time.time()

            # Below threshold
            _, protected_low = service._compute_importance(
                timestamp=now, access_count=4, uniqueness=0.5, now=now, max_age=10000, max_access=100
            )
            assert not protected_low

            # At threshold
            _, protected_at = service._compute_importance(
                timestamp=now, access_count=5, uniqueness=0.5, now=now, max_age=10000, max_access=100
            )
            assert protected_at


class TestAccessTracking:
    """Tests for memory access tracking."""

    def test_query_increments_access_count(self, mock_chromadb):
        """query_memory increments access_count for retrieved memories."""
        from app.services.memory import MemoryService

        mock_chromadb.query.return_value = {
            "ids": [["mem_1", "mem_2"]],
            "documents": [["Doc 1", "Doc 2"]],
            "metadatas": [[{"access_count": 5}, {"access_count": 2}]],
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test query")

            # Verify update was called for each retrieved memory
            assert mock_chromadb.update.call_count == 2

    def test_increment_access_handles_missing_count(self, mock_chromadb):
        """_increment_access_counts handles missing access_count."""
        from app.services.memory import MemoryService

        mock_chromadb.query.return_value = {
            "ids": [["mem_1"]],
            "documents": [["Doc 1"]],
            "metadatas": [[{}]],  # No access_count
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test")

            call_args = mock_chromadb.update.call_args
            assert call_args.kwargs["metadatas"][0]["access_count"] == 1

    def test_increment_access_exception_handling(self, mock_chromadb):
        """_increment_access_counts handles exceptions gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.query.return_value = {
            "ids": [["mem_1"]],
            "documents": [["Doc 1"]],
            "metadatas": [[{"access_count": 0}]],
        }
        mock_chromadb.update.side_effect = Exception("Update failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise, should still return results
            results = service.query_memory("test")
            assert results == ["Doc 1"]


class TestUniquenessScoring:
    """Tests for semantic uniqueness scoring."""

    def test_compute_uniqueness_high_distance(self, mock_chromadb):
        """Memories far from neighbors get high uniqueness scores."""
        from app.services.memory import MemoryService

        # Need at least 2 IDs to trigger uniqueness computation
        mock_chromadb.get.reset_mock()
        mock_chromadb.get.return_value = {
            "ids": ["unique_mem", "distant_mem"],
            "documents": ["Unique content", "Very different"],
            "embeddings": [[0.1] * 384, [0.9] * 384],
        }
        mock_chromadb.query.return_value = {
            "ids": [["unique_mem", "distant_mem"]],
            "distances": [[0.0, 0.8]],  # High distance to neighbors
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            uniqueness = service._compute_uniqueness_scores(["unique_mem", "distant_mem"], mock_chromadb)

            # 0.8 distance / 0.25 = 3.2, capped to 1.0
            assert uniqueness["unique_mem"] >= 0.5

    def test_compute_uniqueness_low_distance(self, mock_chromadb):
        """Memories close to neighbors get lower uniqueness scores."""
        from app.services.memory import MemoryService

        # Need at least 2 IDs to trigger uniqueness computation (single memory is always unique)
        mock_chromadb.get.reset_mock()
        mock_chromadb.get.return_value = {
            "ids": ["common_mem", "similar_mem"],
            "documents": ["Common content", "Similar content"],
            "embeddings": [[0.1] * 384, [0.11] * 384],
        }
        mock_chromadb.query.return_value = {
            "ids": [["common_mem", "similar_mem"]],
            "distances": [[0.0, 0.05]],  # Very close to neighbors
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            uniqueness = service._compute_uniqueness_scores(["common_mem", "similar_mem"], mock_chromadb)

            # 0.05 distance / 0.25 (1.0 - 0.75 threshold) = 0.2
            assert uniqueness["common_mem"] <= 0.5

    def test_compute_uniqueness_single_memory(self, mock_chromadb):
        """Single memory gets default uniqueness of 1.0."""
        from app.services.memory import MemoryService

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            uniqueness = service._compute_uniqueness_scores(["only_mem"], mock_chromadb)

            assert uniqueness["only_mem"] == 1.0

    def test_compute_uniqueness_exception_handling(self, mock_chromadb):
        """Uniqueness computation handles exceptions gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.get.side_effect = Exception("Get failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            uniqueness = service._compute_uniqueness_scores(["mem_1", "mem_2"], mock_chromadb)

            # Should return defaults on error
            assert uniqueness["mem_1"] == 1.0
            assert uniqueness["mem_2"] == 1.0


class TestDeduplication:
    """Tests for semantic deduplication."""

    def test_prune_duplicates_removes_similar(self, mock_chromadb):
        """_prune_duplicates removes semantically similar memories."""
        from app.services.memory import MemoryService

        mock_chromadb.get.return_value = {
            "ids": ["mem_1", "mem_2"],
            "documents": ["Hello world", "Hello world!"],
            "metadatas": [{"timestamp": 1000, "access_count": 10}, {"timestamp": 2000, "access_count": 5}],
        }
        # Simulate high similarity (distance < 0.08 means similarity > 0.92)
        mock_chromadb.query.return_value = {
            "ids": [["mem_1", "mem_2"]],
            "documents": [["Hello world", "Hello world!"]],
            "metadatas": [[{"timestamp": 1000, "access_count": 10}, {"timestamp": 2000, "access_count": 5}]],
            "distances": [[0.0, 0.05]],  # 0.05 distance = 0.95 similarity
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_duplicates(sample_size=10)

            mock_chromadb.delete.assert_called_once()

    def test_prune_duplicates_keeps_high_access(self, mock_chromadb):
        """_prune_duplicates keeps the memory with higher access count."""
        from app.services.memory import MemoryService

        mock_chromadb.get.return_value = {
            "ids": ["mem_1", "mem_2"],
            "documents": ["Same content", "Same content"],
            "metadatas": [
                {"timestamp": 1000, "access_count": 100},  # Higher access
                {"timestamp": 2000, "access_count": 5},
            ],
        }
        mock_chromadb.query.return_value = {
            "ids": [["mem_1", "mem_2"]],
            "documents": [["Same content", "Same content"]],
            "metadatas": [[{"timestamp": 1000, "access_count": 100}, {"timestamp": 2000, "access_count": 5}]],
            "distances": [[0.0, 0.01]],  # Very similar
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_duplicates(sample_size=10)

            deleted = mock_chromadb.delete.call_args.kwargs["ids"]
            assert "mem_2" in deleted  # Lower access count removed
            assert "mem_1" not in deleted

    def test_prune_duplicates_no_similar(self, mock_chromadb):
        """_prune_duplicates skips when no similar memories (only self-matches)."""
        from app.services.memory import MemoryService

        mock_chromadb.get.return_value = {
            "ids": ["mem_1"],
            "documents": ["Apples"],
            "metadatas": [{"timestamp": 1000, "access_count": 0}],
        }
        # Query only returns the same document (no other similar docs)
        mock_chromadb.query.return_value = {
            "ids": [["mem_1"]],
            "documents": [["Apples"]],
            "metadatas": [[{"timestamp": 1000, "access_count": 0}]],
            "distances": [[0.0]],  # Only self-match
        }

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            service._prune_duplicates(sample_size=10, threshold=0.92)

            mock_chromadb.delete.assert_not_called()

    def test_prune_duplicates_exception_handling(self, mock_chromadb):
        """_prune_duplicates handles exceptions gracefully."""
        from app.services.memory import MemoryService

        mock_chromadb.get.side_effect = Exception("Get failed")

        with patch("app.services.memory.service.chromadb.PersistentClient") as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb

            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise
            service._prune_duplicates()
