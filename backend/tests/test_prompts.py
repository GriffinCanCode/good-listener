"""Tests for prompt templates."""
import pytest


class TestSystemPrompt:
    """Tests for system prompt content."""

    def test_system_prompt_exists(self):
        """SYSTEM_PROMPT is defined."""
        from app.services.prompts import SYSTEM_PROMPT
        
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_identity(self):
        """System prompt contains identity info."""
        from app.services.prompts import SYSTEM_PROMPT
        
        assert "Big Ear" in SYSTEM_PROMPT
        assert "good listener" in SYSTEM_PROMPT

    def test_system_prompt_guidelines(self):
        """System prompt contains behavioral guidelines."""
        from app.services.prompts import SYSTEM_PROMPT
        
        assert "NEVER" in SYSTEM_PROMPT
        assert "ALWAYS" in SYSTEM_PROMPT
        assert "markdown" in SYSTEM_PROMPT


class TestAnalysisTemplate:
    """Tests for analysis prompt template."""

    def test_template_exists(self):
        """ANALYSIS_TEMPLATE is defined."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        assert ANALYSIS_TEMPLATE is not None

    def test_template_has_messages(self):
        """Template contains system and human messages."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        # Template should be invokable
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "Test context",
            "memory_context": "",
            "user_query": "Test query"
        })
        
        messages = result.to_messages()
        assert len(messages) >= 2

    def test_template_with_context(self):
        """Template includes context in output."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "Screen shows a login form",
            "memory_context": "User was working on auth",
            "user_query": "How do I login?"
        })
        
        messages = result.to_messages()
        human_msg = messages[-1].content
        
        assert "login form" in human_msg
        assert "How do I login" in human_msg

    def test_template_with_empty_context(self):
        """Template handles empty context."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "",
            "memory_context": "",
            "user_query": "Help me"
        })
        
        messages = result.to_messages()
        assert len(messages) >= 2

    def test_template_system_message_first(self):
        """Template has system message as first message."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        from langchain_core.messages import SystemMessage
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "test",
            "memory_context": "",
            "user_query": "test"
        })
        
        messages = result.to_messages()
        assert isinstance(messages[0], SystemMessage)

    def test_template_human_message_last(self):
        """Template has human message as last message."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        from langchain_core.messages import HumanMessage
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "test",
            "memory_context": "",
            "user_query": "test"
        })
        
        messages = result.to_messages()
        assert isinstance(messages[-1], HumanMessage)

    def test_template_includes_bounding_box_context(self):
        """Template mentions bounding boxes for spatial context."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "[0, 0, 100, 20] Button",
            "memory_context": "",
            "user_query": "Where is the button?"
        })
        
        messages = result.to_messages()
        human_msg = messages[-1].content
        
        assert "bounding box" in human_msg.lower() or "coordinates" in human_msg.lower()


class TestPromptFormatting:
    """Tests for prompt string formatting."""

    def test_context_with_special_chars(self):
        """Template handles special characters in context."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        special_context = "Code: def foo(): return {\"key\": \"value\"}"
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": special_context,
            "memory_context": "",
            "user_query": "Explain this code"
        })
        
        messages = result.to_messages()
        human_msg = messages[-1].content
        
        assert "def foo()" in human_msg

    def test_memory_context_formatting(self):
        """Memory context is included when provided."""
        from app.services.prompts import ANALYSIS_TEMPLATE
        
        result = ANALYSIS_TEMPLATE.invoke({
            "context_text": "Current screen",
            "memory_context": "Previous: User was debugging Python code",
            "user_query": "Continue debugging"
        })
        
        messages = result.to_messages()
        human_msg = messages[-1].content
        
        assert "debugging Python" in human_msg

