from src.utils.CustomAI import CustomAsyncOpenAI
import httpx
from src.config.settings import settings
from src.utils.rate_limiter import nvidia_rate_limiter
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = CustomAsyncOpenAI(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            timeout=180.0
        )

    async def generate_thought_and_content(self, messages: list, thinking: bool = True):
        """Generates content using DeepSeek with optional thinking mode and centralized resilience."""
        try:
            extra_body = {}
            if thinking:
                extra_body = {"chat_template_kwargs": {"thinking": True}}
                
            completion = await self.client.resilient_chat_create(
                model=settings.DEFAULT_MODEL,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=8192,
                extra_body=extra_body,
                stream=True
            )
            
            full_content = ""
            full_thought = ""

            async for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    full_thought += reasoning
                
                if delta.content is not None:
                    full_content += delta.content
            
            return full_thought, full_content
            
        except Exception as e:
            logger.error(f"LLM Final Error: {str(e)}")
            return "", f"Error: {str(e)}"

    async def generate_response_stream(self, messages: list, thinking: bool = True):
        """Yields chunks for SSE streaming with optional thinking mode and centralized resilience."""
        try:
            extra_body = {}
            if thinking:
                extra_body = {"chat_template_kwargs": {"thinking": True}}

            completion = await self.client.resilient_chat_create(
                model=settings.DEFAULT_MODEL,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=8192,
                extra_body=extra_body,
                stream=True
            )
            
            async for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                reasoning = getattr(delta, "reasoning_content", None)
                
                if reasoning or content:
                    yield {
                        "thought": reasoning if reasoning else "",
                        "content": content if content else ""
                    }
                    
        except Exception as e:
            logger.error(f"Stream Final Error: {str(e)}")
            yield {"error": str(e)}
