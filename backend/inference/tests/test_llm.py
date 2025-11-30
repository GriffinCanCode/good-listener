"""Tests for LLMService."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from PIL import Image
import os


class TestLLMService:
    """Tests for LLM analysis service."""

    def test_init_gemini(self):
        """LLMService initializes Gemini provider."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                service = LLMService(provider="gemini", model_name="gemini-2.0-flash")
                
                assert service.provider == "gemini"
                MockGemini.assert_called_once_with(model="gemini-2.0-flash", stream=True)

    def test_init_ollama(self):
        """LLMService initializes Ollama provider."""
        from app.services.llm import LLMService
        
        with patch('langchain_ollama.ChatOllama') as MockOllama:
            service = LLMService(provider="ollama", model_name="llama2")
            
            assert service.provider == "ollama"
            MockOllama.assert_called_once()

    def test_init_no_api_key(self):
        """LLMService handles missing API key for Gemini."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing keys
            os.environ.pop('GOOGLE_API_KEY', None)
            os.environ.pop('GEMINI_API_KEY', None)
            
            with patch('langchain_google_genai.ChatGoogleGenerativeAI'):
                service = LLMService(provider="gemini")
                
                assert service.llm is None

    def test_init_unknown_provider(self):
        """LLMService returns None for unknown provider."""
        from app.services.llm import LLMService
        
        service = LLMService(provider="unknown")
        
        assert service.llm is None

    @pytest.mark.asyncio
    async def test_analyze_no_llm(self):
        """analyze yields error when LLM not configured."""
        from app.services.llm import LLMService
        
        service = LLMService(provider="unknown")
        
        chunks = [c async for c in service.analyze("context", "query")]
        
        assert chunks == ["LLM not configured."]

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """analyze streams response chunks."""
        from app.services.llm import LLMService
        
        async def mock_stream(*args, **kwargs):
            for text in ["Hello ", "World"]:
                chunk = MagicMock()
                chunk.content = text
                yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                chunks = [c async for c in service.analyze("context", "What is this?")]
                
                assert chunks == ["Hello ", "World"]

    @pytest.mark.asyncio
    async def test_analyze_with_image(self):
        """analyze attaches image to message."""
        from app.services.llm import LLMService
        
        async def mock_stream(messages):
            # Verify image was attached
            last_msg = messages[-1]
            assert isinstance(last_msg.content, list)
            assert any(c.get('type') == 'image_url' for c in last_msg.content)
            chunk = MagicMock()
            chunk.content = "Image analyzed"
            yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                image = Image.new('RGB', (100, 100), color='white')
                chunks = [c async for c in service.analyze("context", "query", image)]
                
                assert chunks == ["Image analyzed"]

    @pytest.mark.asyncio
    async def test_analyze_with_memory(self):
        """analyze incorporates memory context."""
        from app.services.llm import LLMService
        
        captured_messages = []
        
        async def mock_stream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock()
            chunk.content = "Response"
            yield chunk
        
        mock_memory = MagicMock()
        mock_memory.query_memory.return_value = ["Previous coding session."]
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini", memory_service=mock_memory)
                chunks = [c async for c in service.analyze("context", "help with code")]
                
                mock_memory.query_memory.assert_called_once_with("help with code", n_results=3)

    @pytest.mark.asyncio
    async def test_analyze_truncates_context(self):
        """analyze truncates long context text."""
        from app.services.llm import LLMService
        
        captured_messages = []
        
        async def mock_stream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock()
            chunk.content = "Done"
            yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                long_context = "x" * 10000  # Over 5000 char limit
                chunks = [c async for c in service.analyze(long_context, "query")]
                
                # Context should be truncated in the prompt
                assert chunks == ["Done"]

    @pytest.mark.asyncio
    async def test_analyze_exception(self):
        """analyze handles LLM exceptions."""
        from app.services.llm import LLMService
        
        async def mock_stream_error(*args, **kwargs):
            raise Exception("API Error")
            yield  # Make it a generator
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream_error
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                chunks = [c async for c in service.analyze("context", "query")]
                
                assert any("Error" in c for c in chunks)

    def test_process_image(self):
        """_process_image converts to base64."""
        from app.services.llm import LLMService
        import base64
        
        service = LLMService(provider="unknown")
        image = Image.new('RGB', (10, 10), color='red')
        
        result = service._process_image(image)
        
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_get_memory_context_no_service(self):
        """_get_memory_context returns empty when no service."""
        from app.services.llm import LLMService
        
        service = LLMService(provider="unknown")
        
        result = service._get_memory_context("query")
        
        assert result == ""

    def test_get_memory_context_no_query(self):
        """_get_memory_context returns empty for empty query."""
        from app.services.llm import LLMService
        
        mock_memory = MagicMock()
        service = LLMService(provider="unknown", memory_service=mock_memory)
        
        result = service._get_memory_context("")
        
        assert result == ""
        mock_memory.query_memory.assert_not_called()

    def test_get_memory_context_with_results(self):
        """_get_memory_context formats memory results."""
        from app.services.llm import LLMService
        
        mock_memory = MagicMock()
        mock_memory.query_memory.return_value = ["Memory 1", "Memory 2"]
        service = LLMService(provider="unknown", memory_service=mock_memory)
        
        result = service._get_memory_context("test query")
        
        assert "Relevant Past Context" in result
        assert "- Memory 1" in result
        assert "- Memory 2" in result


class TestLLMServiceOllama:
    """Tests specific to Ollama provider."""

    def test_init_ollama_custom_host(self):
        """LLMService uses custom Ollama host."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {'OLLAMA_HOST': 'http://custom:11434'}):
            with patch('langchain_ollama.ChatOllama') as MockOllama:
                service = LLMService(provider="ollama", model_name="llama2")
                
                MockOllama.assert_called_once()
                call_kwargs = MockOllama.call_args.kwargs
                assert call_kwargs['base_url'] == 'http://custom:11434'

    def test_init_ollama_default_host(self):
        """LLMService uses default Ollama host when not specified."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('OLLAMA_HOST', None)
            with patch('langchain_ollama.ChatOllama') as MockOllama:
                service = LLMService(provider="ollama", model_name="llama2")
                
                call_kwargs = MockOllama.call_args.kwargs
                assert call_kwargs['base_url'] == 'http://localhost:11434'


class TestLLMServiceImageProcessing:
    """Tests for image processing in LLM."""

    def test_process_image_jpeg_output(self):
        """_process_image outputs JPEG-encoded base64."""
        from app.services.llm import LLMService
        import base64
        
        service = LLMService(provider="unknown")
        image = Image.new('RGB', (50, 50), color='blue')
        
        result = service._process_image(image)
        decoded = base64.b64decode(result)
        
        # JPEG magic bytes
        assert decoded[:2] == b'\xff\xd8'

    def test_process_image_large_image(self):
        """_process_image handles large images."""
        from app.services.llm import LLMService
        
        service = LLMService(provider="unknown")
        large_image = Image.new('RGB', (4000, 3000), color='green')
        
        result = service._process_image(large_image)
        
        assert len(result) > 0

    def test_attach_image_preserves_text(self):
        """_attach_image_if_present preserves original text content."""
        from app.services.llm import LLMService
        from langchain_core.messages import HumanMessage
        
        service = LLMService(provider="unknown")
        messages = [HumanMessage(content="Original text query")]
        image = Image.new('RGB', (10, 10))
        
        result = service._attach_image_if_present(messages, image)
        
        assert result[-1].content[0]['text'] == "Original text query"
        assert result[-1].content[1]['type'] == 'image_url'


class TestLLMServiceContextHandling:
    """Tests for context handling."""

    @pytest.mark.asyncio
    async def test_analyze_empty_context(self):
        """analyze handles empty context text."""
        from app.services.llm import LLMService
        
        async def mock_stream(*args):
            chunk = MagicMock()
            chunk.content = "Response"
            yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                chunks = [c async for c in service.analyze("", "query")]
                
                assert chunks == ["Response"]

    @pytest.mark.asyncio
    async def test_analyze_uses_default_query(self):
        """analyze uses default query when empty."""
        from app.services.llm import LLMService
        
        captured = []
        
        async def mock_stream(messages):
            captured.extend(messages)
            chunk = MagicMock()
            chunk.content = "Done"
            yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                _ = [c async for c in service.analyze("context", "")]  # Empty query
                
                # Template should use "Analyze this screen." as default

    @pytest.mark.asyncio
    async def test_analyze_with_none_image(self):
        """analyze works with None image."""
        from app.services.llm import LLMService
        
        async def mock_stream(*args):
            chunk = MagicMock()
            chunk.content = "Response"
            yield chunk
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                mock_llm = MagicMock()
                mock_llm.astream = mock_stream
                MockGemini.return_value = mock_llm
                
                service = LLMService(provider="gemini")
                chunks = [c async for c in service.analyze("context", "query", None)]
                
                assert chunks == ["Response"]


class TestLLMServiceProviders:
    """Tests for provider selection."""

    def test_gemini_api_key_from_gemini_env(self):
        """LLMService uses GEMINI_API_KEY when GOOGLE_API_KEY is missing."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gemini-key'}, clear=True):
            os.environ.pop('GOOGLE_API_KEY', None)
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                service = LLMService(provider="gemini")
                
                assert service.api_key == 'gemini-key'

    def test_gemini_prefers_google_api_key(self):
        """LLMService prefers GOOGLE_API_KEY over GEMINI_API_KEY."""
        from app.services.llm import LLMService
        
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'google-key',
            'GEMINI_API_KEY': 'gemini-key'
        }):
            with patch('langchain_google_genai.ChatGoogleGenerativeAI') as MockGemini:
                service = LLMService(provider="gemini")
                
                assert service.api_key == 'google-key'

