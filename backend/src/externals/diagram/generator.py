import httpx
import base64
from src.utils.logger import logger

class DiagramGenerator:
    def __init__(self):
        self.base_url = "https://mermaid.ink/img/"

    @staticmethod
    def _encode_mermaid_code(mermaid_code: str) -> str:
        """Return a URL-safe base64 payload suitable for a path segment."""
        code_bytes = mermaid_code.strip().encode("utf-8")
        return base64.urlsafe_b64encode(code_bytes).decode("ascii")

    async def generate_image(self, mermaid_code: str) -> bytes:
        """
        Converts mermaid code to an image using mermaid.ink
        """
        try:
            encoded_mermaid = self._encode_mermaid_code(mermaid_code)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}{encoded_mermaid}", timeout=20.0)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(
                        "Failed to generate diagram: "
                        f"status={response.status_code}, body={response.text[:300]!r}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error generating diagram: {str(e)}")
            return None

diagram_generator = DiagramGenerator()
