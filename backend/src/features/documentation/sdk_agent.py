import json
import logging
import re
from src.database.repository import DocumentationRepository
from src.externals.diagram.generator import diagram_generator
from src.config.settings import settings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.externals.llm.client import LLMClient

logger = logging.getLogger(__name__)

class SDKDocumentationAgent:
    """A lightweight, LangChain-free agent using direct OpenAI SDK calls."""
    
    def __init__(
        self,
        repo: DocumentationRepository,
        llm: "LLMClient",
        project_id: Optional[int] = None,
        content_preferences: Optional[dict[str, bool]] = None,
    ):
        self.repo = repo
        self.llm = llm
        self.project_id = project_id
        self.content_preferences = {
            "include_code": True,
            "include_flowcharts": True,
            "include_graphs": True,
            "include_charts": True,
            **(content_preferences or {}),
        }
        
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
                            "mermaid_code": {"type": "string", "description": "The mermaid diagram code."},
                            "caption": {"type": "string", "description": "A short, descriptive caption for the diagram."},
                            "diagram_kind": {
                                "type": "string",
                                "enum": ["flowchart", "graph", "chart"],
                                "description": "Classify the diagram as a flowchart, graph, or chart."
                            }
                        },
                        "required": ["title", "mermaid_code", "diagram_kind"]
                    }
                }
            }
        ]

    async def _write_section(self, title: str, section_name: str, section_content: str) -> str:
        # Strip unwated markdown fences if AI included them
        clean_content = re.sub(r'^```markdown\n', '', section_content.strip(), flags=re.IGNORECASE)
        clean_content = re.sub(r'^```\w*\n', '', clean_content, flags=re.IGNORECASE)
        clean_content = clean_content.rstrip('`').strip()
        clean_content = self._sanitize_section_content(clean_content, self.content_preferences)

        # Use project_id if available, otherwise fallback to title (legacy)
        if self.project_id:
            await self.repo.save_section(self.project_id, section_name, clean_content)
        else:
            project = await self.repo.get_or_create_project(title, "", 10)
            await self.repo.save_section(project.id, section_name, clean_content)
        return f"Successfully saved section: {section_name}"

    @staticmethod
    def _normalize_diagram_kind(diagram_kind: Optional[str], mermaid_code: str) -> str:
        if diagram_kind in {"flowchart", "graph", "chart"}:
            return diagram_kind

        first_line = next((line.strip().lower() for line in mermaid_code.splitlines() if line.strip()), "")
        if first_line.startswith(("pie", "gantt", "timeline", "xychart", "quadrantchart")):
            return "chart"
        if first_line.startswith(("classdiagram", "erdiagram", "mindmap", "architecture-beta", "block-beta")):
            return "graph"
        return "flowchart"

    def _diagram_kind_allowed(self, diagram_kind: str) -> bool:
        return self.content_preferences.get(
            {
                "flowchart": "include_flowcharts",
                "graph": "include_graphs",
                "chart": "include_charts",
            }.get(diagram_kind, "include_flowcharts"),
            True,
        )

    @staticmethod
    def _is_meta_commentary_line(line: str) -> bool:
        plain = re.sub(r"^[>\-\*\+\d\.\)\s#`_]+", "", line or "")
        plain = re.sub(r"\s+", " ", plain).strip().lower()
        if not plain:
            return False

        if re.search(
            r"\b(?:as an ai|language model|assistant|system prompt|prompt|chain of thought|reasoning|internal note|thinking aloud)\b",
            plain,
        ):
            return True

        if re.match(r"^(?:thought|reasoning|analysis|plan|internal note|draft)\s*:", plain):
            return True

        if plain in {"ok", "okay", "sure", "certainly", "absolutely", "alright"}:
            return True

        conversational_open = re.match(
            r"^(?:ok(?:ay)?|sure|certainly|absolutely|alright|let me|let's|here(?:'s| is)|below is|i(?:'ll| will| need to| am|’m)|we(?:'ll| will))\b",
            plain,
        )
        planning_verb = re.search(
            r"\b(?:need to|will|going to|plan to|write|draft|outline|explain|provide|generate|cover|walk through|structure|organize|start with|continue)\b",
            plain,
        )
        meta_object = re.search(
            r"\b(?:section|document|response|output|answer|writeup|draft|documentation|content|request|prompt|task)\b",
            plain,
        )

        if conversational_open and (planning_verb or meta_object):
            return True

        if (
            re.search(r"\b(?:i|we|let's|let us)\b", plain)
            and planning_verb
            and meta_object
            and len(plain) <= 280
        ):
            return True

        if (
            re.match(r"^(?:this section|the following section|in this section)\b", plain)
            and re.search(r"\b(?:will|covers?|provides?|discuss(?:es)?|explains?)\b", plain)
            and len(plain) <= 220
        ):
            return True

        return False

    @classmethod
    def _remove_meta_commentary(cls, content: str) -> str:
        content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"write_section\(\s*\{[\s\S]*?\}\s*\)", "", content)

        cleaned_lines = []
        in_code_block = False

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                cleaned_lines.append(line)
                continue

            if not in_code_block and cls._is_meta_commentary_line(line):
                continue

            cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)
        return re.sub(r"\n{3,}", "\n\n", cleaned_content).strip()

    @classmethod
    def _sanitize_section_content(cls, content: str, preferences: dict[str, bool]) -> str:
        content = cls._remove_meta_commentary(content)

        def replace_diagram_call(match: re.Match[str]) -> str:
            json_blob = match.group(1)
            diagram_kind = None
            mermaid_code = ""

            try:
                payload = json.loads(json_blob)
                diagram_kind = payload.get("diagram_kind")
                mermaid_code = payload.get("mermaid_code", "") or payload.get("code", "") or payload.get("content", "")
            except Exception:
                mermaid_match = re.search(r'"(?:mermaid_code|code|content)"\s*:\s*"(.*?)"', json_blob, re.DOTALL)
                if mermaid_match:
                    mermaid_code = mermaid_match.group(1).replace("\\n", "\n").replace('\\"', '"')
                kind_match = re.search(r'"diagram_kind"\s*:\s*"(flowchart|graph|chart)"', json_blob)
                if kind_match:
                    diagram_kind = kind_match.group(1)

            diagram_kind = cls._normalize_diagram_kind(diagram_kind, mermaid_code)
            if preferences.get(
                {
                    "flowchart": "include_flowcharts",
                    "graph": "include_graphs",
                    "chart": "include_charts",
                }[diagram_kind],
                True,
            ):
                return match.group(0)
            return ""

        content = re.sub(
            r"generate_diagram\(\s*(\{[\s\S]*?\})\s*\)",
            replace_diagram_call,
            content,
        )

        def replace_fenced_block(match: re.Match[str]) -> str:
            language = (match.group(1) or "").strip().lower()
            body = match.group(2)

            if language == "mermaid":
                diagram_kind = cls._normalize_diagram_kind(None, body)
                if preferences.get(
                    {
                        "flowchart": "include_flowcharts",
                        "graph": "include_graphs",
                        "chart": "include_charts",
                    }[diagram_kind],
                    True,
                ):
                    return match.group(0)
                return ""

            if not preferences.get("include_code", True):
                return ""

            return match.group(0)

        content = re.sub(r"```(\w+)?\n([\s\S]*?)```", replace_fenced_block, content)
        content = cls._remove_meta_commentary(content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        return content

    async def _generate_diagram(
        self,
        title: str,
        mermaid_code: str,
        caption: str = "",
        diagram_kind: str = "flowchart",
    ) -> str:
        diagram_kind = self._normalize_diagram_kind(diagram_kind, mermaid_code)
        if not self._diagram_kind_allowed(diagram_kind):
            return f"Skipping disabled {diagram_kind} generation."

        # Use project_id if available, otherwise fallback to title (legacy)
        p_id = self.project_id
        if not p_id:
            project = await self.repo.get_or_create_project(title, "", 10)
            p_id = project.id
            
        img_bytes = await diagram_generator.generate_image(mermaid_code)
        if img_bytes:
            await self.repo.add_diagram(p_id, img_bytes, caption)
            return "Diagram generated and attached."
        return "Failed to generate diagram."

    async def run(self, mission: str):
        """Executes the reasoning loop for a specific mission."""
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are the Lead Documentation Architect. Write dense, high-value technical markdown. "
                    "STRICTLY BE CONCISE. Stick to the provided context; tag any additions as '(Future Enhancement)'. "
                    "Use neutral, document-style prose only. "
                    "Do not include conversational preambles, authorial narration, or meta commentary such as "
                    "'Okay', 'Here is', 'I will', 'we will', 'this section will', or references to prompts, tasks, or reasoning. "
                    "Do NOT wrap your entire response in markdown code fences (triple backticks ``````). "
                    "Starting your response with ``` is STRICTLY FORBIDDEN. "
                    f"Content preferences: code={'enabled' if self.content_preferences['include_code'] else 'disabled'}, "
                    f"flowcharts={'enabled' if self.content_preferences['include_flowcharts'] else 'disabled'}, "
                    f"graphs={'enabled' if self.content_preferences['include_graphs'] else 'disabled'}, "
                    f"charts={'enabled' if self.content_preferences['include_charts'] else 'disabled'}. "
                    "Treat disabled artifact types as hard constraints. "
                    "If you call generate_diagram, always include diagram_kind as flowchart, graph, or chart. "
                    "Once the section is finalized, call write_section with the completed markdown only."
                )
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
