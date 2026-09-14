import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import assert_hospital_access, get_db, get_tenant_context
from app.core.tenant_context import TenantContext
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
)
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/hospitals", tags=["Knowledge"])


@router.post(
    "/{hospital_id}/knowledge",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a knowledge document",
)
async def create_knowledge_document(
    hospital_id: uuid.UUID,
    body: KnowledgeDocumentCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    assert_hospital_access(tenant, hospital_id)
    doc = await knowledge_service.create_document(db, hospital_id, body, tenant)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.get(
    "/{hospital_id}/knowledge",
    response_model=list[KnowledgeDocumentResponse],
    summary="List knowledge documents — tenant-scoped",
)
async def list_knowledge_documents(
    hospital_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    assert_hospital_access(tenant, hospital_id)
    docs = await knowledge_service.list_documents(db, hospital_id, tenant)
    return [KnowledgeDocumentResponse.model_validate(d) for d in docs]


@router.post(
    "/{hospital_id}/knowledge/search",
    response_model=list[KnowledgeDocumentResponse],
    summary="Search knowledge documents — always scoped to this hospital",
)
async def search_knowledge(
    hospital_id: uuid.UUID,
    body: KnowledgeSearchRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    assert_hospital_access(tenant, hospital_id)
    docs = await knowledge_service.search_documents(db, hospital_id, body, tenant)
    return [KnowledgeDocumentResponse.model_validate(d) for d in docs]


@router.get(
    "/{hospital_id}/knowledge/{doc_id}",
    response_model=KnowledgeDocumentResponse,
    summary="Get a single knowledge document (validates hospital ownership)",
)
async def get_knowledge_document(
    hospital_id: uuid.UUID,
    doc_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    assert_hospital_access(tenant, hospital_id)
    doc = await knowledge_service.get_document(db, doc_id, tenant)
    return KnowledgeDocumentResponse.model_validate(doc)
