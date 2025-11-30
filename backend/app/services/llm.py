import os
import json
import httpx
import logging
import google.generativeai as genai
from typing import AsyncGenerator, Optional
from PIL import Image
import io
import base64
from app.services.prompts import get_analysis_prompt

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, provider: str = "gemini", model_name: str = "gemini-2.0-flash", memory_service=None):
        self.provider = provider
        self.model_name = model_name
        self.memory_service = memory_service
        
        # Setup Gemini using GOOGLE_API_KEY (standard) or GEMINI_API_KEY
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.provider == "gemini":
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini initialized with model: {self.model_name}")
            else:
                logger.warning("Gemini provider selected but no API key found (GOOGLE_API_KEY or GEMINI_API_KEY).")
                self.gemini_model = None

    async def analyze(self, context_text: str, user_query: str = "", image: Optional[Image.Image] = None) -> AsyncGenerator[str, None]:
        memory_context = ""
        if self.memory_service and user_query:
            if memories := self.memory_service.query_memory(user_query, n_results=3):
                memory_context = "\nRelevant Past Context:\n" + "\n".join(f"- {m}" for m in memories)

        prompt = get_analysis_prompt(context_text, memory_context, user_query)

        if self.provider == "gemini":
            async for chunk in self._call_gemini(prompt, image):
                yield chunk
        elif self.provider == "ollama":
            async for chunk in self._call_ollama(prompt, image if "llava" in self.model_name else None):
                yield chunk
        else:
            yield "Invalid LLM provider configured."

    async def _call_ollama(self, prompt: str, image: Optional[Image.Image] = None) -> AsyncGenerator[str, None]:
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True
            }
            
            if image:
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                payload["images"] = [img_str]

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=30.0
                ) as response:
                    if response.status_code != 200:
                        error_text = ""
                        try: error_text = (await response.aread()).decode()
                        except: pass
                        yield f"Ollama Error: {response.status_code} {error_text}"
                        return

                    async for line in response.aiter_lines():
                        if not line: continue
                        try:
                            data = json.loads(line)
                            text = data.get("response", "")
                            if text: yield text
                            if data.get("done"): break
                        except json.JSONDecodeError: continue
        except Exception as e:
            yield f"Ollama connection failed: {e}"

    async def _call_gemini(self, prompt: str, image: Optional[Image.Image] = None) -> AsyncGenerator[str, None]:
        try:
            if not self.gemini_model:
                yield "Gemini not configured. Missing API Key."
                return
            
            content = [prompt]
            if image:
                content.append(image)

            response = await self.gemini_model.generate_content_async(content, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Gemini Error: {e}"
