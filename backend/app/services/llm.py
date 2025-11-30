import os
import json
import httpx
import google.generativeai as genai
from typing import AsyncGenerator

class LLMService:
    def __init__(self, provider: str = "ollama", model_name: str = "gpt-oss:20b"):
        self.provider = provider
        self.model_name = model_name
        
        # Setup Gemini if needed
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.provider == "gemini" and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')

    async def analyze(self, context_text: str, user_query: str = "") -> AsyncGenerator[str, None]:
        prompt = f"""
        Context from screen (OCR):
        {context_text[:2000]} 
        
        User Query: {user_query if user_query else "Analyze this and provide key insights."}
        
        Please provide a concise, helpful response.
        """

        if self.provider == "ollama":
            async for chunk in self._call_ollama(prompt):
                yield chunk
        elif self.provider == "gemini":
            async for chunk in self._call_gemini(prompt):
                yield chunk
        else:
            yield "Invalid LLM provider configured."

    async def _call_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": True
                    },
                    timeout=30.0
                ) as response:
                    if response.status_code != 200:
                        error_text = ""
                        try:
                            error_text = (await response.aread()).decode()
                        except:
                            pass
                        yield f"Ollama Error: {response.status_code} {error_text}"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            text = data.get("response", "")
                            if text:
                                yield text
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"Failed to connect to Ollama: {e}. Is it running?"

    async def _call_gemini(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            if not self.gemini_model:
                yield "Gemini not configured. missing API Key."
                return
            
            response = await self.gemini_model.generate_content_async(prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Gemini Error: {e}"
