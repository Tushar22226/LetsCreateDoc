import json
import logging
from src.externals.llm.client import LLMClient
from src.database.repository import DocumentationRepository
from src.externals.diagram.generator import diagram_generator
from src.config.settings import settings
from typing import Optional

logger = logging.getLogger(__name__)

class SDKDocumentationAgent:
    """A lightweight, LangChain-free agent using direct OpenAI SDK calls."""
    
    def __init__(self, repo: DocumentationRepository, llm: LLMClient, project_id: Optional[int] = None):
        self.repo = repo
        self.llm = llm
        self.project_id = project_id
        
        # Tool mapping
        self.tools = {
            "write_section": self._write_section,
            "generate_diagram": self._generate_diagram
        }
        
        self.tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "write_section",
                    "description": "Stores the generated markdown content for a specific section.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The project title."},
                            "section_name": {"type": "string", "description": "The name of the section."},
                            "section_content": {"type": "string", "description": "The markdown content."}
                        },
                        "required": ["title", "section_name", "section_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_diagram",
                    "description": "Converts mermaid code into an image and attaches it to the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The project title."},
                            "mermaid_code": {"type": "string", "description": "The mermaid diagram code."}
                        },
                        "required": ["title", "mermaid_code"]
                    }
                }
            }
        ]

    async def _write_section(self, title: str, section_name: str, section_content: str) -> str:
        import re
        # Strip unwated markdown fences if AI included them
        clean_content = re.sub(r'^```markdown\n', '', section_content.strip(), flags=re.IGNORECASE)
        clean_content = re.sub(r'^```\w*\n', '', clean_content, flags=re.IGNORECASE)
        clean_content = clean_content.rstrip('`').strip()

        # Use project_id if available, otherwise fallback to title (legacy)
        if self.project_id:
            await self.repo.save_section(self.project_id, section_name, clean_content)
        else:
            project = await self.repo.get_or_create_project(title, "", 10)
            await self.repo.save_section(project.id, section_name, clean_content)
        return f"Successfully saved section: {section_name}"

    async def _generate_diagram(self, title: str, mermaid_code: str) -> str:
        # Use project_id if available, otherwise fallback to title (legacy)
        p_id = self.project_id
        if not p_id:
            project = await self.repo.get_or_create_project(title, "", 10)
            p_id = project.id
            
        img_bytes = await diagram_generator.generate_image(mermaid_code)
        if img_bytes:
            await self.repo.add_diagram(p_id, img_bytes)
            return "Diagram generated and attached."
        return "Failed to generate diagram."

    async def run(self, mission: str):
        """Executes the reasoning loop for a specific mission."""
        messages = [
            {
                "role": "system", 
                "content": "You are the Lead Documentation Architect. Write dense, high-value technical markdown. STRICTLY BE CONCISE. Stick to the provided context; tag any additions as '(Future Enhancement)'. MINIMIZE CODE blocks; use them only if critical. Do NOT wrap your entire response in markdown code fences (triple backticks ``````). Starting your response with ``` is STRICTLY FORBIDDEN. Limit to one Mermaid diagram per section only if critical."
            },
            {"role": "user", "content": mission}
        ]
        
        # Simple 1-turn reasoning loop for performance (can be extended)
        try:
            # We use the resilient client but bypass LangChain's ainvoke
            completion = await self.llm.client.resilient_chat_create(
                model=settings.DEFAULT_MODEL,
                messages=messages,
                tools=self.tool_definitions,
                tool_choice="auto"
            )
            
            message = completion.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if function_name in self.tools:
                        logger.info(f"SDK Agent calling tool: {function_name}")
                        await self.tools[function_name](**args)
            
            return message.content or "Task completed via tools."
            
        except Exception as e:
            logger.error(f"SDK Agent Error: {str(e)}")
            raise e
