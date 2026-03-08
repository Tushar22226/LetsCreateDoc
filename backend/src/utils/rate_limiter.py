import asyncio
import time
from typing import Optional
from src.utils.logger import logger

class RateLimiter:
    """No-op rate limiter as requested to 'let it rip'."""
    def __init__(self, rpm: int = 40, capacity: int = 5):
        pass

    async def wait(self):
        return

# Globally shared rate limiter for NVIDIA API
# Burst support and RPM logic disabled per user request
nvidia_rate_limiter = RateLimiter()
