import json
import asyncio
import io
import re
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel, Field, field_validator
from src.database.repository import DocumentationRepository
from src.externals.llm.client import LLMClient
from src.features.documentation.sdk_agent import SDKDocumentationAgent
from src.utils.docx_generator import DOCXGenerator
from src.utils.logger import logger
from src.features.documentation.prompts import SYSTEM_PROMPT_PLANNER, SYSTEM_PROMPT_WRITER, MISSION_TEMPLATE

class Section(BaseModel):
    title: str
    description: Optional[str] = None

DEFAULT_THEME_COLOR = "#1F4E79"


class ProjectInput(BaseModel):
    title: str
    description: str
    page_count: int = 10
    custom_index: List[Section] = Field(default_factory=list)
    comment: Optional[str] = None
    theme_color: str = DEFAULT_THEME_COLOR
    include_code: bool = True
    include_flowcharts: bool = True
    include_graphs: bool = True
    include_charts: bool = True
    regenerate: bool = False # Flag to bypass cache

    @field_validator("theme_color")
    @classmethod
    def validate_theme_color(cls, value: str) -> str:
        cleaned = (value or DEFAULT_THEME_COLOR).strip()
        if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", cleaned):
            raise ValueError("theme_color must be a 6-digit hex color")
        cleaned = cleaned.upper()
        return cleaned if cleaned.startswith("#") else f"#{cleaned}"

    def content_preferences(self) -> dict[str, bool]:
        return {
            "include_code": self.include_code,
            "include_flowcharts": self.include_flowcharts,
            "include_graphs": self.include_graphs,
            "include_charts": self.include_charts,
        }

class StreamCleaner:
    def __init__(self):
        self.buffer = ""
        self.prefix_stripped = False
    
    def clean(self, chunk: str) -> str:
        if self.prefix_stripped:
            return chunk
        self.buffer += chunk
        
        # Check if we have enough to detect a prefix
        # We strip leading whitespace for the check but keep internal structure
        temp_buffer = self.buffer.lstrip()
        if not temp_buffer:
            return ""

        prefixes = ["```markdown", "```md", "```"]
        for p in prefixes:
            if temp_buffer.startswith(p):
                # If the buffer ends right after the prefix line, we've stripped it
                # Looking for the newline after the fence
                newline_idx = temp_buffer.find('\n')
                if newline_idx != -1:
                    # We found the end of the fence line
                    self.buffer = temp_buffer[newline_idx+1:]
                    self.prefix_stripped = True
                    return self.buffer
                return "" # Still looking for the newline after the ```markdown
        
        # If we have content that clearly doesn't start with a fence
        if len(temp_buffer) > 20:
            self.prefix_stripped = True
            return self.buffer
            
        return "" # Still buffering prefix

class DocumentationService:
    def __init__(self, repo: DocumentationRepository, llm: LLMClient):
        self.repo = repo
        self.llm = llm
        self.agent = SDKDocumentationAgent(repo, llm)
        self.semaphore = asyncio.Semaphore(10) # Increased concurrency per user request

    def _normalize_title(self, title: str) -> str:
        """Removes Markdown bolding, italics, and extra whitespace for consistent cache keys."""
        if not title: return ""
        # Remove ** and * but keep the text
        return re.sub(r'[\*\#\_]', '', title).strip()

    def _build_generation_preferences(self, project_input: ProjectInput) -> str:
        option_lines = [
            f"- Code snippets or pseudo-code: {'Enabled' if project_input.include_code else 'Disabled'}",
            f"- Flowcharts and sequence/state flows: {'Enabled' if project_input.include_flowcharts else 'Disabled'}",
            f"- Graphs and relationship diagrams: {'Enabled' if project_input.include_graphs else 'Disabled'}",
            f"- Charts and metric visualizations: {'Enabled' if project_input.include_charts else 'Disabled'}",
        ]

        disabled = []
        if not project_input.include_code:
            disabled.append("code snippets")
        if not project_input.include_flowcharts:
            disabled.append("flowcharts")
        if not project_input.include_graphs:
            disabled.append("graphs")
        if not project_input.include_charts:
            disabled.append("charts")

        if disabled:
            option_lines.append(
                f"- Hard rule: do not plan, generate, mention as placeholders, or save these disabled artifacts: {', '.join(disabled)}."
            )
        else:
            option_lines.append("- Hard rule: all optional artifact types are enabled.")

        if not any([project_input.include_flowcharts, project_input.include_graphs, project_input.include_charts]):
            option_lines.append("- Use prose, tables, and headings only for visual explanation. Do not call diagram tools.")

        return "\n".join(option_lines)

    async def generate_full_document(self, project_input: ProjectInput, project_id: Optional[int] = None) -> bytes:
        """Compiles the final sections into a DOCX file, with project ID continuity."""
        if project_id:
            project = await self.repo.get_project_by_id(project_id)
            if project:
                project = await self.repo.update_project_metadata(
                    project.id,
                    project_input.title,
                    project_input.description,
                    project_input.page_count,
                    project_input.theme_color,
                )
        else:
            project = await self.repo.get_or_create_project(
                project_input.title,
                project_input.description,
                project_input.page_count,
                project_input.theme_color,
            )

        if not project:
            project = await self.repo.create_project(
                project_input.title,
                project_input.description,
                project_input.page_count,
                project_input.theme_color,
            )
            
        # Ensure agent uses this project ID
        self.agent = SDKDocumentationAgent(
            self.repo,
            self.llm,
            project_id=project.id,
            content_preferences=project_input.content_preferences(),
        )
            
        sections = project_input.custom_index
        if not sections or len(sections) == 0:
            if project.plan:
                logger.info("Using cached plan from database...")
                plan_md = project.plan
            else:
                logger.info("No custom index or cached plan provided, generating one...")
                plan_md, _ = await self.generate_doc_plan(project_input)
                await self.repo.update_project_plan(project.id, plan_md)
            
            raw_titles = [line.lstrip('# ').strip() for line in plan_md.split('\n') if line.startswith('#') or line.startswith('##')]
            if not raw_titles: raw_titles = ["Introduction", "Core Architecture", "API Implementation", "Deployment", "Maintenance"]
            sections = [Section(title=self._normalize_title(t)) for t in raw_titles]
            
        logger.info(f"Sections to generate: {len(sections)}")
        
        # 2. Iterate through sections
        front_matter_sections = [
            {
                "title": self._normalize_title(section.title),
                "description": section.description,
            }
            for section in sections
        ]

        docx = DOCXGenerator(theme_color=project_input.theme_color)
        docx.add_title_page(
            project_input.title,
            description=project_input.description,
            page_count=project_input.page_count,
            sections=front_matter_sections,
        )
        
        for i, section in enumerate(sections):
            normalized_title = self._normalize_title(section.title)
            logger.info(f"Finalizing section {i+1}/{len(sections)}: {normalized_title}")
            
            # Check if we already have content (from streaming)
            content = await self.repo.get_section_content(project.id, normalized_title)
            
            if not content:
                logger.info(f"No cached content for {section.title}, invoking agent...")
                mission = MISSION_TEMPLATE.format(
                    section_title=section.title,
                    project_description=project_input.description,
                    section_description=section.description if section.description else "Use general project context.",
                    generation_preferences=self._build_generation_preferences(project_input),
                    page_weight=f"{project_input.page_count / len(sections):.1f}"
                )
                
                try:
                    async with self.semaphore:
                        await self.agent.run(mission)
                    content = await self.repo.get_section_content(project.id, normalized_title)
                    if not content:
                        content = "Section generation failed."
                except Exception as e:
                    logger.error(f"Error generating section {section.title}: {str(e)}")
                    content = f"Error generating content: {str(e)}"

            content = SDKDocumentationAgent._sanitize_section_content(
                content,
                project_input.content_preferences(),
            )
            await docx.add_markdown_section(normalized_title, content)
            
            # Add any diagrams generated during this section
            project_diagrams = await self.repo.get_project_diagrams(project.id)
            if project_diagrams:
                for j, (img_bytes, diag_cap) in enumerate(project_diagrams):
                    docx.add_image(img_bytes, diag_cap if diag_cap else f"Diagram {i+1}.{j+1}")
                # Clear diagrams for next section
                await self.repo.cleanup_project_diagrams(project.id)

        return docx.get_docx_bytes().getvalue()

    async def stream_doc_plan(self, project_input: ProjectInput) -> AsyncGenerator[str, None]:
        """Streams the detailed documentation plan. Always fresh project."""
        project = await self.repo.create_project(
            project_input.title,
            project_input.description,
            project_input.page_count,
            project_input.theme_color,
        )
        
        yield f"data: {json.dumps({'status': 'planning_started', 'id': project.id})}\n\n"
        
        formatted_planner_system = SYSTEM_PROMPT_PLANNER.format(
            page_count=project_input.page_count,
            generation_preferences=self._build_generation_preferences(project_input),
        )
        
        plan_md = ""
        cleaner = StreamCleaner()
        async with self.semaphore:
            # PERFORMANCE: Disable 'thinking' for planning to get near-instant blueprints
            async for chunk in self.llm.generate_response_stream(
                [
                    {"role": "system", "content": formatted_planner_system},
                    {
                        "role": "user",
                        "content": (
                            f"Project: {project_input.title}\n"
                            f"Description: {project_input.description}\n"
                            f"Comment: {project_input.comment or 'None'}"
                        ),
                    }
                ], 
                thinking=False
            ):
                if "error" in chunk:
                    yield f"data: {json.dumps({'status': 'error', 'message': chunk['error']})}\n\n"
                    return
                cleaned_chunk = cleaner.clean(chunk['content'])
                plan_md += cleaned_chunk # FIXED: Save cleaned content
                yield f"data: {json.dumps({'status': 'planning_progress', 'content': cleaned_chunk})}\n\n"
        
        await self.repo.update_project_plan(project.id, plan_md)
        yield f"data: {json.dumps({'status': 'planning_completed', 'plan': plan_md, 'id': project.id})}\n\n"

    async def generate_doc_plan(self, project_input: ProjectInput) -> tuple[str, int]:
        """Generates a detailed documentation plan. legacy non-streaming version."""
        project = await self.repo.create_project(
            project_input.title,
            project_input.description,
            project_input.page_count,
            project_input.theme_color,
        )
        
        formatted_planner_system = SYSTEM_PROMPT_PLANNER.format(
            page_count=project_input.page_count,
            generation_preferences=self._build_generation_preferences(project_input),
        )
        async with self.semaphore:
            _thought, plan = await self.llm.generate_thought_and_content(
                [
                    {"role": "system", "content": formatted_planner_system},
                    {
                        "role": "user",
                        "content": (
                            f"Project: {project_input.title}\n"
                            f"Description: {project_input.description}\n"
                            f"Comment: {project_input.comment or 'None'}"
                        ),
                    }
                ], 
                thinking=False
            )
        
        # Strip fences from one-shot plan
        plan = re.sub(r'^```markdown\n', '', plan.strip(), flags=re.MULTILINE)
        plan = re.sub(r'^```\n?', '', plan, flags=re.MULTILINE)
        plan = plan.rstrip('`').strip()
        
        await self.repo.update_project_plan(project.id, plan)
        return plan, project.id

    async def stream_generation(self, project_input: ProjectInput, project_id: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Streams the generation process section-by-section using SSE with parallel backend work."""
        if project_id:
            project = await self.repo.get_project_by_id(project_id)
            if project:
                project = await self.repo.update_project_metadata(
                    project.id,
                    project_input.title,
                    project_input.description,
                    project_input.page_count,
                    project_input.theme_color,
                )
            else:
                # Fallback if ID is invalid
                project = await self.repo.create_project(
                    project_input.title,
                    project_input.description,
                    project_input.page_count,
                    project_input.theme_color,
                )
        else:
            project = await self.repo.create_project(
                project_input.title,
                project_input.description,
                project_input.page_count,
                project_input.theme_color,
            )
            
        # Re-initialize agent with THIS specific project_id for tool continuity
        self.agent = SDKDocumentationAgent(
            self.repo,
            self.llm,
            project_id=project.id,
            content_preferences=project_input.content_preferences(),
        )
        sections = project_input.custom_index
        
        # 1. Generate Index with streaming if not provided
        if not sections:
            # SMART CACHE: Check if inputs changed
            inputs_changed = (
                project.description != project_input.description or 
                project.page_count != project_input.page_count
            )

            if project.plan and not project_input.regenerate and not inputs_changed:
                logger.info(f"Using cached plan for: {project_input.title}")
                plan_md = project.plan
                yield f"data: {json.dumps({'status': 'planning_completed', 'plan': plan_md, 'cached': True})}\n\n"
            else:
                if inputs_changed:
                    logger.info(f"Inputs changed for {project_input.title}, forced regeneration")
                yield f"data: {json.dumps({'status': 'planning_started'})}\n\n"
                plan_md = ""
                formatted_planner_system = SYSTEM_PROMPT_PLANNER.format(
                    page_count=project_input.page_count,
                    generation_preferences=self._build_generation_preferences(project_input),
                )
                
                cleaner = StreamCleaner()
                async with self.semaphore:
                    # PERFORMANCE: Disable 'thinking' for planning
                    async for chunk in self.llm.generate_response_stream(
                        [
                            {"role": "system", "content": formatted_planner_system},
                            {
                                "role": "user",
                                "content": (
                                    f"Project: {project_input.title}\n"
                                    f"Description: {project_input.description}\n"
                                    f"Comment: {project_input.comment or 'None'}"
                                ),
                            }
                        ],
                        thinking=False
                    ):
                        if "error" in chunk:
                            yield f"data: {json.dumps({'status': 'error', 'message': chunk['error']})}\n\n"
                            return
                        cleaned_chunk = cleaner.clean(chunk['content'])
                        plan_md += cleaned_chunk # FIXED: Save cleaned content
                        yield f"data: {json.dumps({'status': 'planning_progress', 'thought': chunk['thought'], 'content': cleaned_chunk})}\n\n"
                
                await self.repo.update_project_plan(project.id, plan_md)
                yield f"data: {json.dumps({'status': 'planning_completed', 'plan': plan_md})}\n\n"
            
            raw_titles = [line.lstrip('# ').strip() for line in plan_md.split('\n') if line.startswith('#') or line.startswith('##')]
            if not raw_titles: raw_titles = ["Introduction", "Core Architecture", "API Implementation", "Deployment", "Maintenance"]
            sections = [Section(title=self._normalize_title(t)) for t in raw_titles]

        yield f"data: {json.dumps({'status': 'started', 'total_sections': len(sections)})}\n\n"

        # Create a buffer for each section's stream
        buffers = [asyncio.Queue() for _ in sections]
        tasks = []
        
        async def generate_section_task(idx: int, section: Section):
            cleaner = StreamCleaner()
            try:
                mission = MISSION_TEMPLATE.format(
                    section_title=section.title,
                    project_description=project_input.description,
                    section_description=section.description if section.description else "Use general project context.",
                    generation_preferences=self._build_generation_preferences(project_input),
                    page_weight=f"{project_input.page_count / len(sections):.1f}"
                )
                
                await buffers[idx].put({'status': 'generating', 'section': section.title, 'index': idx})
                section_content = ""
                
                async with self.semaphore:
                    async for chunk in self.llm.generate_response_stream([
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT_WRITER.format(
                                generation_preferences=self._build_generation_preferences(project_input)
                            ),
                        },
                        {"role": "user", "content": mission}
                    ], thinking=False):
                        if "error" in chunk:
                            await buffers[idx].put({'status': 'error', 'message': chunk['error']})
                        else:
                            cleaned_chunk = cleaner.clean(chunk['content'] if chunk['content'] else "")
                            section_content += cleaned_chunk # FIXED: Save cleaned content
                            
                            if cleaned_chunk or chunk['thought']:
                                await buffers[idx].put({
                                    'status': 'progress', 
                                    'thought': chunk['thought'], 
                                    'content': cleaned_chunk
                                })
                
                # Save to document store for final DOCX compilation
                normalized_section_title = self._normalize_title(section.title)
                sanitized_content = SDKDocumentationAgent._sanitize_section_content(
                    section_content,
                    project_input.content_preferences(),
                )
                await self.repo.save_section(
                    project.id,
                    normalized_section_title,
                    sanitized_content,
                    order_index=idx,
                    description=section.description,
                )
                
                await buffers[idx].put({'status': 'completed_section', 'section': section.title})
            except Exception as e:
                logger.error(f"Parallel Task Error [Section {idx}]: {str(e)}")
                await buffers[idx].put({'status': 'error', 'message': str(e)})
            finally:
                await buffers[idx].put(None) # Always signal end

        try:
            # Launch all agents in parallel
            for i, section in enumerate(sections):
                tasks.append(asyncio.create_task(generate_section_task(i, section)))

            # Sequentially drain the buffers
            for i in range(len(sections)):
                while True:
                    item = await buffers[i].get()
                    if item is None:
                        break
                    yield f"data: {json.dumps(item)}\n\n"

            # Mark project completed
            await self.repo.update_project_status(project.id, "completed")
            
            logger.info(f"Stream generation finished for: {project_input.title}")
            yield f"data: {json.dumps({'status': 'finished', 'docx_ready': True})}\n\n"
        
        except asyncio.CancelledError:
            logger.warning(f"Stream generation cancelled for: {project_input.title}")
            raise
        finally:
            # Clean up background tasks
            for t in tasks:
                if not t.done():
                    t.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def get_project_history(self) -> List[dict]:
        """Fetches all past document generations."""
        projects = await self.repo.get_all_projects()
        return [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "page_count": p.page_count,
                "theme_color": p.theme_color,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in projects
        ]
        
    async def generate_docx_from_id(self, project_id: int) -> Optional[bytes]:
        """Compiles a DOCX from a previously saved project and its sections."""
        project = await self.repo.get_project_by_id(project_id)
        if not project:
            return None
            
        sections = await self.repo.get_project_sections(project.id)
        diagrams = await self.repo.get_project_diagrams(project.id)
        
        front_matter_sections = [
            {
                "title": section.title,
                "description": section.description,
            }
            for section in sections
        ]

        docx = DOCXGenerator(theme_color=project.theme_color)
        docx.add_title_page(
            project.title,
            description=project.description or "",
            page_count=project.page_count,
            sections=front_matter_sections,
        )
        
        # We don't have exact diagram mappings for past disconnected streams yet, 
        # so we append all diagrams at the end as an appendix if any exist
        for section in sections:
            cleaned_content = SDKDocumentationAgent._sanitize_section_content(
                section.content or "",
                {
                    "include_code": True,
                    "include_flowcharts": True,
                    "include_graphs": True,
                    "include_charts": True,
                },
            )
            await docx.add_markdown_section(section.title, cleaned_content)
            
        if diagrams:
            await docx.add_markdown_section("Appendix: Architecture Diagrams", "Below are the diagrams generated for this project.")
            for i, (img_bytes, diag_cap) in enumerate(diagrams):
                docx.add_image(img_bytes, diag_cap if diag_cap else f"Diagram {i+1}")
                
        return docx.get_docx_bytes().getvalue()
