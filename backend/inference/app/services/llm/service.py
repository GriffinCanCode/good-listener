import base64
import io
import os
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage
from PIL import Image

from app.core import get_logger
from app.services.constants import CONTEXT_TEXT_MAX_LENGTH, MEMORY_QUERY_RESULTS
from app.services.llm.prompts import ANALYSIS_TEMPLATE

logger = get_logger(__name__)


class LLMService:
    def __init__(self, provider: str = "gemini", model_name: str = "gemini-2.0-flash", memory_service=None):
        self.provider, self.model_name, self.memory_service = provider, model_name, memory_service
        if api_key := os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key
        self.api_key = api_key
        self.llm = self._init_llm()

    def _init_llm(self):
        match self.provider:
            case "gemini" if self.api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI

                return ChatGoogleGenerativeAI(model=self.model_name, stream=True)
            case "gemini":
                logger.warning("Gemini provider selected but no API key found.")
            case "ollama":
                from langchain_ollama import ChatOllama

                return ChatOllama(model=self.model_name, base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        return None

    async def analyze(self, context_text: str, user_query: str = "", image: Image.Image | None = None) -> AsyncGenerator[str, None]:
        if not self.llm:
            yield "LLM not configured."
            return
        msgs = ANALYSIS_TEMPLATE.invoke({
            "context_text": context_text[:CONTEXT_TEXT_MAX_LENGTH] if context_text else "No text detected via OCR.",
            "memory_context": self._get_memory_context(user_query),
            "user_query": user_query or "Analyze this screen.",
        }).to_messages()
        if image:
            msgs[-1] = HumanMessage(content=[
                {"type": "text", "text": msgs[-1].content},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self._encode_image(image)}"}},
            ])
        try:
            async for chunk in self.llm.astream(msgs):
                yield chunk.content
        except Exception as e:
            logger.exception("LLM Error")
            yield f"Error: {e}"

    def _get_memory_context(self, query: str) -> str:
        if self.memory_service and query and (memories := self.memory_service.query_memory(query, n_results=MEMORY_QUERY_RESULTS)):
            return "\nRelevant Past Context:\n" + "\n".join(f"- {m}" for m in memories)
        return ""

    def _encode_image(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode()
