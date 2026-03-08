import httpx
import base64
from src.utils.logger import logger

class DiagramGenerator:
    def __init__(self):
        self.base_url = "https://mermaid.ink/img/"

    async def generate_image(self, mermaid_code: str) -> bytes:
        """
        Converts mermaid code to an image using mermaid.ink
        """
        try:
            # Clean up mermaid code
            code_bytes = mermaid_code.encode('utf-8')
            base64_string = base64.b64encode(code_bytes).decode('utf-8')
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}{base64_string}")
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Failed to generate diagram: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error generating diagram: {str(e)}")
            return None

diagram_generator = DiagramGenerator()
