from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import TenantContext
from app.models.knowledge_document import KnowledgeDocument, KnowledgeDocumentStatus
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeSearchRequest
from app.services.audit_service import audit_service


class KnowledgeService:
    """
    Tenant-aware knowledge service.

    Phase 1: Plain-text PostgreSQL search (ILIKE).
    Future:  Replace DB search with Vector DB similarity search +
             metadata filter { hospital_id: tenant.hospital_id }.
             The security boundary (hospital_id filter) NEVER changes.
    """

    async def create_document(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        data: KnowledgeDocumentCreate,
        tenant: TenantContext,
    ) -> KnowledgeDocument:
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        doc = KnowledgeDocument(
            id=uuid.uuid4(),
            hospital_id=hospital_id,  # Tenant-locked
            protocol_id=data.protocol_id,
            title=data.title,
            content=data.content,
            version=data.version,
            status=KnowledgeDocumentStatus.ACTIVE,
        )
        db.add(doc)
        await db.flush()

        await audit_service.log_event(
            db=db,
            action="KNOWLEDGE_DOCUMENT_CREATED",
            actor_user_id=tenant.user_id,
            hospital_id=hospital_id,
            resource_type="KNOWLEDGE_DOCUMENT",
            resource_id=doc.id,
            metadata={"title": data.title},
        )
        await db.commit()
        await db.refresh(doc)
        return doc

    async def list_documents(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        tenant: TenantContext,
    ) -> list[KnowledgeDocument]:
        """
        Always filters by tenant.hospital_id — hospital_id arg is verified, not trusted.
        """
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        # ← Security boundary: always tenant-scoped
        scoped_id = hospital_id if tenant.is_platform_admin else tenant.hospital_id

        result = await db.execute(
            select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.hospital_id == scoped_id,
                    KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE,
                )
            )
        )
        return list(result.scalars().all())

    async def search_documents(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        request: KnowledgeSearchRequest,
        tenant: TenantContext,
    ) -> list[KnowledgeDocument]:
        """
        Full-text search within a hospital's knowledge base.

        The query is ALWAYS AND-ed with hospital_id = tenant.hospital_id.
        A Hospital A user will NEVER see Hospital B's documents.

        Future RAG replacement:
            vector_store.similarity_search(
                query=request.query,
                filter={"hospital_id": str(tenant.hospital_id)},  # ← same boundary
                k=request.limit,
            )
        """
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")

        scoped_id = hospital_id if tenant.is_platform_admin else tenant.hospital_id

        query = select(KnowledgeDocument).where(
            and_(
                KnowledgeDocument.hospital_id == scoped_id,
                KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE,
                KnowledgeDocument.content.ilike(f"%{request.query}%"),
            )
        ).limit(request.limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_document(
        self,
        db: AsyncSession,
        doc_id: uuid.UUID,
        tenant: TenantContext,
    ) -> KnowledgeDocument:
        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Knowledge document not found.")
        # Direct-ID attack prevention
        if not tenant.can_access_hospital(doc.hospital_id):
            raise HTTPException(status_code=403, detail="Access denied.")
        return doc


knowledge_service = KnowledgeService()
