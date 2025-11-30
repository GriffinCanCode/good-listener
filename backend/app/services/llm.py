import os
import logging
import base64
import io
from typing import AsyncGenerator, Optional
from PIL import Image

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from app.services.prompts import ANALYSIS_TEMPLATE, MONITOR_TEMPLATE

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, provider: str = "gemini", model_name: str = "gemini-2.0-flash", memory_service=None):
        self.provider = provider
        self.model_name = model_name
        self.memory_service = memory_service
        
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key

        self.llm = self._init_llm()

    def _init_llm(self):
        if self.provider == "gemini":
            if not self.api_key:
                logger.warning("Gemini provider selected but no API key found.")
                return None
            return ChatGoogleGenerativeAI(model=self.model_name, stream=True)
        elif self.provider == "ollama":
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            return ChatOllama(model=self.model_name, base_url=host)
        return None

    async def analyze(self, context_text: str, user_query: str = "", image: Optional[Image.Image] = None) -> AsyncGenerator[str, None]:
        if not self.llm:
            yield "LLM not configured."
            return

        # Truncate context to avoid excessive token usage, similar to original logic
        context_text = context_text[:5000] if context_text else "No text detected via OCR."
        memory_ctx = self._get_memory_context(user_query)
        
        # Format the prompt messages using the template
        prompt_val = ANALYSIS_TEMPLATE.invoke({
            "context_text": context_text, 
            "memory_context": memory_ctx, 
            "user_query": user_query or "Analyze this screen."
        })
        
        messages = prompt_val.to_messages()
        messages = self._attach_image_if_present(messages, image)

        try:
            async for chunk in self.llm.astream(messages):
                yield chunk.content
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            yield f"Error: {e}"

    async def monitor_chat(self, transcript: str, screen_ctx: str, image: Optional[Image.Image] = None) -> AsyncGenerator[str, None]:
        if not self.llm:
            yield "LLM not configured."
            return

        prompt_val = MONITOR_TEMPLATE.invoke({
            "transcript": transcript,
            "screen_ctx": screen_ctx
        })
        messages = prompt_val.to_messages()
        messages = self._attach_image_if_present(messages, image)

        try:
            async for chunk in self.llm.astream(messages):
                yield chunk.content
        except Exception as e:
            logger.error(f"Monitor LLM Error: {e}")
            yield f"Error: {e}"

    def _attach_image_if_present(self, messages, image: Optional[Image.Image]):
        if image:
            content_text = messages[-1].content
            image_data = self._process_image(image)
            messages[-1] = HumanMessage(content=[
                {"type": "text", "text": content_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ])
        return messages

    def _get_memory_context(self, query: str) -> str:
        if self.memory_service and query:
            if memories := self.memory_service.query_memory(query, n_results=3):
                return "\nRelevant Past Context:\n" + "\n".join(f"- {m}" for m in memories)
        return ""

    def _process_image(self, image: Image.Image) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
