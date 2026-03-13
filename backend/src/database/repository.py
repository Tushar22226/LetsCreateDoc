from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from src.database.models import Project, Section, Diagram

import asyncio

class DocumentationRepository:
    """Data Access Layer for the Documentation feature, handling all database IO."""
    def __init__(self, session: AsyncSession):
        self.session = session
        self.lock = asyncio.Lock()
        
    async def create_project(self, title: str, description: str, page_count: int, theme_color: str = "#1F4E79", plan: str = None) -> Project:
        """Always creates a NEW project record for every generation request."""
        async with self.lock:
            project = Project(
                title=title,
                description=description,
                page_count=page_count,
                theme_color=theme_color,
                plan=plan,
                status="generating"
            )
            self.session.add(project)
            await self.session.commit()
            await self.session.refresh(project)
            return project

    async def get_or_create_project(self, title: str, description: str, page_count: int, theme_color: str = "#1F4E79", plan: str = None) -> Project:
        # Legacy method kept but now aliases to create_project to satisfy existing calls 
        # while fulfilling the user's request for fresh state.
        return await self.create_project(title, description, page_count, theme_color, plan)

    async def update_project_metadata(self, project_id: int, title: str, description: str, page_count: int, theme_color: str) -> Optional[Project]:
        async with self.lock:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project = result.scalars().first()
            if not project:
                return None

            project.title = title
            project.description = description
            project.page_count = page_count
            project.theme_color = theme_color
            await self.session.commit()
            await self.session.refresh(project)
            return project

    async def update_project_plan(self, project_id: int, plan: str) -> None:
        async with self.lock:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project = result.scalars().first()
            if project:
                project.plan = plan
                await self.session.commit()
            
    async def update_project_status(self, project_id: int, status: str) -> None:
        async with self.lock:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project = result.scalars().first()
            if project:
                project.status = status
                await self.session.commit()
                
    async def get_all_projects(self) -> List[Project]:
        async with self.lock:
            stmt = select(Project).order_by(Project.created_at.desc())
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
    async def get_project_by_id(self, project_id: int) -> Optional[Project]:
        async with self.lock:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            return result.scalars().first()
            
    async def save_section(self, project_id: int, title: str, content: str, order_index: int = 0, description: str = None) -> Section:
        async with self.lock:
            stmt = select(Section).where(
                (Section.project_id == project_id) & 
                (Section.title == title)
            )
            result = await self.session.execute(stmt)
            section = result.scalars().first()
            
            if section:
                section.content = content
                if description:
                    section.description = description
                section.order_index = order_index
            else:
                section = Section(
                    project_id=project_id,
                    title=title,
                    content=content,
                    description=description,
                    order_index=order_index
                )
                self.session.add(section)
                
            await self.session.commit()
            await self.session.refresh(section)
            return section
            
    async def get_section_content(self, project_id: int, title: str) -> Optional[str]:
        async with self.lock:
            # 1. Exact match
            stmt = select(Section).where(
                (Section.project_id == project_id) & 
                (Section.title == title)
            )
            result = await self.session.execute(stmt)
            section = result.scalars().first()
            
            if section: return section.content
            
            # 2. Case-insensitive / Normalize match
            stmt = select(Section).where(Section.project_id == project_id)
            result = await self.session.execute(stmt)
            all_sections = result.scalars().all()
            
            def normalize(t): return "".join(t.lower().split())
            
            target = normalize(title)
            for s in all_sections:
                if normalize(s.title) == target:
                    return s.content
                
        return None

    async def get_project_sections(self, project_id: int) -> List[Section]:
        async with self.lock:
            stmt = select(Section).where(Section.project_id == project_id).order_by(Section.order_index)
            result = await self.session.execute(stmt)
            return result.scalars().all()

    async def add_diagram(self, project_id: int, image_bytes: bytes, caption: str = None) -> Diagram:
        import base64
        async with self.lock:
            # Store bytes as base64 string
            b64_image = base64.b64encode(image_bytes).decode('utf-8')
            diagram = Diagram(
                project_id=project_id,
                image_data=b64_image,
                caption=caption
            )
            self.session.add(diagram)
            await self.session.commit()
            await self.session.refresh(diagram)
            return diagram
            
    async def get_project_diagrams(self, project_id: int) -> List[tuple]:
        import base64
        stmt = select(Diagram).where(Diagram.project_id == project_id)
        result = await self.session.execute(stmt)
        diagrams = result.scalars().all()
        
        return [(base64.b64decode(d.image_data), d.caption) for d in diagrams]
            
    async def cleanup_project_diagrams(self, project_id: int) -> None:
        async with self.lock:
            stmt = select(Diagram).where(Diagram.project_id == project_id)
            result = await self.session.execute(stmt)
            diagrams = result.scalars().all()
            for d in diagrams:
                await self.session.delete(d)
            await self.session.commit()
