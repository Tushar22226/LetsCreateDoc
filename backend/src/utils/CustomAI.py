from typing import Any, Optional
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
import httpx
import asyncio
import time
from src.utils.logger import logger
from src.utils.rate_limiter import nvidia_rate_limiter

class CustomAI:
    """Lightweight wrapper for LLM calls with streamlined retry logic."""
    def __init__(self, *args, **kwargs):
        pass

    # Note: We are now primarily using CustomAsyncOpenAI below 
    # for direct SDK calls to avoid any LangChain-related issues.

class CustomAsyncOpenAI(AsyncOpenAI):
    """Custom AsyncOpenAI that provides a resilient way to call completions."""
    
    def __init__(self, *args, **kwargs):
        # Defensively strip max_retries from SDK init
        kwargs.pop("max_retries", None)
        # Ensure we have a robust http_client if one isn't provided
        if "http_client" not in kwargs:
            kwargs["http_client"] = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(180.0, connect=10.0, read=180.0),
                follow_redirects=True
            )
        super().__init__(*args, **kwargs)

    async def resilient_chat_create(self, retries: int = 3, **kwargs):
        """Wraps chat.completions.create with streamlined retry logic."""
        # ABSOLUTE FIX: Forcefully strip max_retries before it hits the SDK completions.create()
        kwargs.pop("max_retries", None)
        
        for attempt in range(retries):
            try:
                await nvidia_rate_limiter.wait() 
                return await self.chat.completions.create(**kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["429", "rate limit", "504", "502", "gateway", "connection", "timeout"]):
                    wait_time = min((attempt + 1) * 2, 20)
                    logger.warning(f"Resilient Client Error (attempt {attempt+1}): {str(e)}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise e
        return await self.chat.completions.create(**kwargs)