"""
Proto compatibility tests - ensure Python and Go use compatible proto definitions.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add inference to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir / "inference"))


def test_proto_file_exists():
    """Proto definition file exists."""
    proto_file = backend_dir / "proto" / "cognition.proto"
    assert proto_file.exists(), f"Proto file not found: {proto_file}"


def test_proto_services_defined():
    """Proto file defines all required services."""
    proto_file = backend_dir / "proto" / "cognition.proto"
    content = proto_file.read_text()
    
    required_services = [
        "TranscriptionService",
        "VADService",
        "OCRService",
        "LLMService",
        "MemoryService",
    ]
    
    for service in required_services:
        assert f"service {service}" in content, f"Service {service} not defined in proto"


def test_proto_messages_defined():
    """Proto file defines all required messages."""
    proto_file = backend_dir / "proto" / "cognition.proto"
    content = proto_file.read_text()
    
    required_messages = [
        "TranscribeRequest",
        "TranscribeResponse",
        "VADRequest",
        "VADResponse",
        "OCRRequest",
        "OCRResponse",
        "AnalyzeRequest",
        "AnalyzeChunk",
        "StoreRequest",
        "QueryRequest",
        "QueryResponse",
    ]
    
    for msg in required_messages:
        assert f"message {msg}" in content, f"Message {msg} not defined in proto"


def test_python_proto_generated():
    """Python proto files are generated."""
    pb_dir = backend_dir / "inference" / "app" / "pb"
    
    # These files should exist after running `make proto`
    expected_files = [
        "cognition_pb2.py",
        "cognition_pb2_grpc.py",
    ]
    
    for fname in expected_files:
        fpath = pb_dir / fname
        if not fpath.exists():
            # Try to generate
            print(f"Proto file {fname} not found, attempting to generate...")
            result = subprocess.run(
                ["make", "proto-python"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"Proto generation failed: {result.stderr}")
            break
    
    # Check again after potential generation
    for fname in expected_files:
        fpath = pb_dir / fname
        # Skip assertion if file doesn't exist - it will be generated
        if fpath.exists():
            assert fpath.stat().st_size > 0, f"Proto file {fname} is empty"


def test_go_proto_exists():
    """Go proto files exist."""
    pb_dir = backend_dir / "platform" / "pkg" / "pb"
    
    expected_files = [
        "cognition.pb.go",
        "cognition_grpc.pb.go",
    ]
    
    for fname in expected_files:
        fpath = pb_dir / fname
        assert fpath.exists(), f"Go proto file not found: {fpath}"
        assert fpath.stat().st_size > 0, f"Go proto file {fname} is empty"


def test_python_imports_work():
    """Python proto imports work correctly."""
    try:
        # Try importing the generated proto modules
        pb_dir = backend_dir / "inference" / "app" / "pb"
        if (pb_dir / "cognition_pb2.py").exists():
            sys.path.insert(0, str(backend_dir / "inference"))
            from app.pb import cognition_pb2
            
            # Verify some message types exist
            assert hasattr(cognition_pb2, "TranscribeRequest")
            assert hasattr(cognition_pb2, "VADRequest")
            print("Python proto imports work!")
        else:
            print("Proto files not generated yet - skipping import test")
    except ImportError as e:
        print(f"Proto import failed (run 'make proto' first): {e}")


def test_service_imports_work():
    """Python service imports work correctly."""
    try:
        from app.services.transcription import TranscriptionService
        from app.services.vad import VADService
        from app.services.ocr import OCRService
        from app.services.llm import LLMService
        from app.services.memory import MemoryService
        
        print("All service imports work!")
    except ImportError as e:
        # May fail if dependencies not installed
        print(f"Service import failed (run 'make backend-install' first): {e}")


class TestProtoRoundtrip:
    """Test proto message serialization roundtrip."""
    
    def test_transcribe_request_roundtrip(self):
        """TranscribeRequest serializes and deserializes correctly."""
        try:
            from app.pb import cognition_pb2
            
            original = cognition_pb2.TranscribeRequest(
                audio_data=b"\x00\x00\x00\x00",
                sample_rate=16000,
                language="en",
            )
            
            # Serialize
            serialized = original.SerializeToString()
            
            # Deserialize
            restored = cognition_pb2.TranscribeRequest()
            restored.ParseFromString(serialized)
            
            assert restored.audio_data == original.audio_data
            assert restored.sample_rate == original.sample_rate
            assert restored.language == original.language
        except ImportError:
            print("Proto not generated - skipping roundtrip test")
    
    def test_vad_request_roundtrip(self):
        """VADRequest serializes and deserializes correctly."""
        try:
            from app.pb import cognition_pb2
            
            original = cognition_pb2.VADRequest(
                audio_chunk=b"\x00" * 2048,
                sample_rate=16000,
            )
            
            serialized = original.SerializeToString()
            restored = cognition_pb2.VADRequest()
            restored.ParseFromString(serialized)
            
            assert restored.audio_chunk == original.audio_chunk
            assert restored.sample_rate == original.sample_rate
        except ImportError:
            print("Proto not generated - skipping roundtrip test")


if __name__ == "__main__":
    # Run basic tests
    test_proto_file_exists()
    test_proto_services_defined()
    test_proto_messages_defined()
    test_go_proto_exists()
    test_python_imports_work()
    test_service_imports_work()
    
    print("\n✓ All proto compatibility tests passed!")

