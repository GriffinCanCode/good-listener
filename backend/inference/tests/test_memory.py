"""Tests for MemoryService."""
import pytest
from unittest.mock import MagicMock, patch
import time


class TestMemoryService:
    """Tests for vector memory storage."""

    def test_init_success(self, mock_chromadb):
        """MemoryService initializes ChromaDB client."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test_chroma")
            
            assert service.client is not None
            assert service.collection is not None

    def test_init_failure(self):
        """MemoryService handles init failure gracefully."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient', side_effect=Exception("Failed")):
            with patch('os.path.exists', return_value=True):
                service = MemoryService()
                
                assert service.client is None
                assert service.collection is None

    def test_add_memory_success(self, mock_chromadb):
        """add_memory stores text in collection."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("Test memory content", "audio")
            
            mock_chromadb.add.assert_called_once()
            call_args = mock_chromadb.add.call_args
            assert call_args.kwargs['documents'] == ["Test memory content"]
            assert call_args.kwargs['metadatas'][0]['source'] == "audio"

    def test_add_memory_empty_text(self, mock_chromadb):
        """add_memory skips empty text."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("   ", "audio")
            
            mock_chromadb.add.assert_not_called()

    def test_add_memory_no_collection(self):
        """add_memory handles missing collection."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient', side_effect=Exception("Failed")):
            with patch('os.path.exists', return_value=True):
                service = MemoryService()
                # Should not raise
                service.add_memory("Test", "audio")

    def test_add_memory_with_metadata(self, mock_chromadb):
        """add_memory includes custom metadata."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            custom_meta = {"topic": "code", "language": "python"}
            service.add_memory("Code snippet", "screen", metadata=custom_meta)
            
            call_args = mock_chromadb.add.call_args
            metadata = call_args.kwargs['metadatas'][0]
            assert metadata['topic'] == "code"
            assert metadata['language'] == "python"
            assert metadata['source'] == "screen"

    def test_add_memory_triggers_prune(self, mock_chromadb):
        """add_memory prunes when count exceeds threshold."""
        from app.services.memory import MemoryService
        
        mock_chromadb.count.return_value = 10001  # Over threshold
        mock_chromadb.get.return_value = {'ids': [f"audio_{i}" for i in range(10001)]}
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("Test", "audio")
            
            mock_chromadb.delete.assert_called_once()

    def test_query_memory_success(self, mock_chromadb):
        """query_memory returns matching documents."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("coding help", n_results=3)
            
            mock_chromadb.query.assert_called_once()
            assert results == ['Previous context about coding.']

    def test_query_memory_with_filter(self, mock_chromadb):
        """query_memory passes metadata filter."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", filter_metadata={"source": "screen"})
            
            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs['where'] == {"source": "screen"}

    def test_query_memory_no_collection(self):
        """query_memory returns empty list when no collection."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient', side_effect=Exception("Failed")):
            with patch('os.path.exists', return_value=True):
                service = MemoryService()
                results = service.query_memory("test")
                
                assert results == []

    def test_query_memory_empty_results(self, mock_chromadb):
        """query_memory handles empty results."""
        from app.services.memory import MemoryService
        
        mock_chromadb.query.return_value = {'documents': [[]]}
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("nonexistent")
            
            assert results == []

    def test_query_memory_exception(self, mock_chromadb):
        """query_memory handles exceptions gracefully."""
        from app.services.memory import MemoryService
        
        mock_chromadb.query.side_effect = Exception("Query failed")
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            results = service.query_memory("test")
            
            assert results == []

    def test_prune_oldest(self, mock_chromadb):
        """_prune_oldest removes old memories."""
        from app.services.memory import MemoryService
        
        # Create IDs with timestamps
        old_ids = [f"audio_{1000 + i}" for i in range(6000)]
        mock_chromadb.get.return_value = {'ids': old_ids}
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service._prune_oldest(keep=5000)
            
            mock_chromadb.delete.assert_called_once()
            deleted_ids = mock_chromadb.delete.call_args.kwargs['ids']
            assert len(deleted_ids) == 1000  # 6000 - 5000 = 1000 to delete

    def test_ensure_data_dir(self):
        """_ensure_data_dir creates directory if missing."""
        from app.services.memory import MemoryService
        
        with patch('os.path.exists', return_value=False) as mock_exists:
            with patch('os.makedirs') as mock_makedirs:
                with patch('app.services.memory.chromadb.PersistentClient'):
                    service = MemoryService(persistence_path="/tmp/new_dir")
                    
                    mock_makedirs.assert_called_with("/tmp/new_dir", exist_ok=True)


class TestMemoryServiceEdgeCases:
    """Edge case tests for MemoryService."""

    def test_add_memory_whitespace_only(self, mock_chromadb):
        """add_memory skips whitespace-only text."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.add_memory("\t\n  ", "audio")
            
            mock_chromadb.add.assert_not_called()

    def test_add_memory_exception_handling(self, mock_chromadb):
        """add_memory handles add exception gracefully."""
        from app.services.memory import MemoryService
        
        mock_chromadb.add.side_effect = Exception("Add failed")
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise
            service.add_memory("Test content", "audio")

    def test_query_memory_with_special_characters(self, mock_chromadb):
        """query_memory handles special characters in query."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("def func(): return {}", n_results=3)
            
            mock_chromadb.query.assert_called_once()

    def test_query_memory_large_n_results(self, mock_chromadb):
        """query_memory handles large n_results."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", n_results=1000)
            
            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs['n_results'] == 1000

    def test_add_memory_preserves_custom_timestamp(self, mock_chromadb):
        """add_memory preserves custom timestamp in metadata."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            custom_meta = {"timestamp": 1234567890}
            service.add_memory("Test", "screen", metadata=custom_meta)
            
            call_args = mock_chromadb.add.call_args
            assert call_args.kwargs['metadatas'][0]['timestamp'] == 1234567890

    def test_prune_oldest_no_ids(self, mock_chromadb):
        """_prune_oldest handles empty ID list."""
        from app.services.memory import MemoryService
        
        mock_chromadb.get.return_value = {'ids': []}
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service._prune_oldest(keep=5000)
            
            mock_chromadb.delete.assert_not_called()

    def test_prune_oldest_under_threshold(self, mock_chromadb):
        """_prune_oldest skips when under threshold."""
        from app.services.memory import MemoryService
        
        mock_chromadb.get.return_value = {'ids': [f"audio_{i}" for i in range(100)]}
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service._prune_oldest(keep=5000)
            
            mock_chromadb.delete.assert_not_called()

    def test_prune_oldest_exception(self, mock_chromadb):
        """_prune_oldest handles exceptions gracefully."""
        from app.services.memory import MemoryService
        
        mock_chromadb.get.side_effect = Exception("Get failed")
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            # Should not raise
            service._prune_oldest(keep=5000)


class TestMemoryServiceConcurrency:
    """Tests for concurrent memory operations."""

    def test_add_memory_generates_unique_ids(self, mock_chromadb):
        """add_memory generates unique IDs for concurrent calls."""
        from app.services.memory import MemoryService
        import time
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            
            service.add_memory("First", "audio")
            time.sleep(0.002)  # Ensure different timestamp
            service.add_memory("Second", "audio")
            
            calls = mock_chromadb.add.call_args_list
            id1 = calls[0].kwargs['ids'][0]
            id2 = calls[1].kwargs['ids'][0]
            
            assert id1 != id2

    def test_query_memory_none_filter(self, mock_chromadb):
        """query_memory handles None filter_metadata."""
        from app.services.memory import MemoryService
        
        with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
            MockClient.return_value.get_or_create_collection.return_value = mock_chromadb
            
            service = MemoryService(persistence_path="/tmp/test")
            service.query_memory("test", filter_metadata=None)
            
            call_args = mock_chromadb.query.call_args
            assert call_args.kwargs['where'] is None

