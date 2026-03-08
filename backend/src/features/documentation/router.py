from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from src.features.documentation.service import DocumentationService, ProjectInput
from src.database.repository import DocumentationRepository
from src.database.db import get_db
from src.externals.llm.client import LLMClient
import io
import re
import json

# --- Annotated Type Aliases for Dependency Injection ---

DbSession = Annotated[AsyncSession, Depends(get_db)]
RepoDepend = Annotated[DocumentationRepository, Depends()]
LLMDepend = Annotated[LLMClient, Depends()]

def get_repo(session: DbSession) -> DocumentationRepository:
    """Provides a DocumentationRepository with an injected database session."""
    return DocumentationRepository(session)

def get_service(
    repo: Annotated[DocumentationRepository, Depends(get_repo)],
    llm: LLMDepend,
) -> DocumentationService:
    """Provides a fully injected DocumentationService."""
    return DocumentationService(repo, llm)

# Annotated alias for the service — use this in all endpoints
ServiceDepend = Annotated[DocumentationService, Depends(get_service)]

router = APIRouter(prefix="/documentation", tags=["Documentation"])


@router.post("/generate-plan")
async def generate_plan(
    project_input: ProjectInput,
    service: ServiceDepend,
):
    plan, project_id = await service.generate_doc_plan(project_input)
    return {"plan": plan, "id": project_id}


@router.get("/stream-plan")
async def stream_plan(
    title: str,
    description: str,
    page_count: int,
    service: ServiceDepend,
    comment: str = "",
):
    project_input = ProjectInput(
        title=title,
        description=description,
        page_count=page_count,
        comment=comment,
    )

    return StreamingResponse(
        service.stream_doc_plan(project_input),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("/stream-generation")
async def stream_generation(
    title: str,
    description: str,
    page_count: int,
    service: ServiceDepend,
    custom_index: str = "",
    comment: str = "",
    regenerate: bool = False,
    project_id: Optional[int] = None,
):
    parsed_index = []
    if custom_index:
        try:
            parsed_index = json.loads(custom_index)
        except Exception:
            pass

    project_input = ProjectInput(
        title=title,
        description=description,
        page_count=page_count,
        custom_index=parsed_index,
        comment=comment,
        regenerate=regenerate,
    )

    # We pass project_id directly to the stream method if provided
    return StreamingResponse(
        service.stream_generation(project_input, project_id=project_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.post("/generate-index")
async def generate_index(
    project_input: ProjectInput,
    service: ServiceDepend,
):
    plan = await service.generate_doc_plan(project_input)
    return {"index": plan}


@router.post("/generate-docx")
async def generate_docx(
    project_input: ProjectInput,
    service: ServiceDepend,
    project_id: Optional[int] = None,
):
    docx_bytes = await service.generate_full_document(project_input, project_id=project_id)
    safe_title = re.sub(r'[^a-zA-Z0-9\s\._-]', '', project_input.title).strip() or "document"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.docx"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/history")
async def get_history(service: ServiceDepend):
    projects = await service.get_project_history()
    return {"projects": projects}


@router.get("/download/{project_id}")
async def download_history_docx(
    project_id: int,
    service: ServiceDepend,
):
    docx_bytes = await service.generate_docx_from_id(project_id)
    if not docx_bytes:
        raise HTTPException(status_code=404, detail="Project or documents not found.")

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="past_document_{project_id}.docx"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
