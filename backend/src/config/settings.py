from dotenv import load_dotenv
load_dotenv()
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    DEFAULT_MODEL: str = "deepseek-ai/deepseek-v3.1"
    GEMINI_API_KEY: str = ""
    APP_NAME: str = "LetsCreateDoc"
    
    class Config:
        env_file = ".env"

settings = Settings()
