import asyncio
from typing import List, Optional, Dict
from langchain_core.tools import tool
from src.externals.llm.client import LLMClient
from src.externals.diagram.generator import diagram_generator
from src.utils.rate_limiter import nvidia_rate_limiter
from src.utils.docx_generator import DOCXGenerator
from src.utils.logger import logger
import io

from src.database.repository import DocumentationRepository

def get_documentation_toolkit(repo: DocumentationRepository, llm: LLMClient) -> list:
    """Returns LangChain tools injected with the database repository and LLM client."""
    
    @tool
    async def draft_index(title: str, description: str, page_count: int) -> List[str]:
        """Generates a structured table of contents for the documentation."""
        prompt = f"""
        Generate a detailed, structured table of contents for project documentation.
        Title: {title}
        Description: {description}
        Target length: {page_count} pages.
        
        Return a clean list of section titles.
        """
        thought, content = await llm.generate_thought_and_content([{"role": "user", "content": prompt}])
        index = [line.strip().lstrip('1234567890. -') for line in content.split('\n') if line.strip()]
        
        # Ensure project space is created
        await repo.get_or_create_project(title, description, page_count)
            
        return index

    @tool
    async def write_section(title: str, section_name: str, section_content: str) -> str:
        """Stores the generated content for a specific section.
        
        Args:
            title: The project title.
            section_name: The name of the section.
            section_content: The actual markdown content written.
        """
        project = await repo.get_or_create_project(title, "", 10)
        await repo.save_section(project.id, section_name, section_content)
        return f"Successfully saved section: {section_name}"

    @tool
    async def generate_diagram(title: str, mermaid_code: str, caption: str = "") -> str:
        """Converts mermaid code into an image and stores it for the project.
        
        Args:
            title: The project title.
            mermaid_code: The mermaid diagram code.
            caption: A short, descriptive caption for the diagram.
        """
        project = await repo.get_or_create_project(title, "", 10)
        img_bytes = await diagram_generator.generate_image(mermaid_code)
        if img_bytes:
            await repo.add_diagram(project.id, img_bytes, caption)
            return "Diagram generated and attached."
        return "Failed to generate diagram."

    return [draft_index, write_section, generate_diagram]
