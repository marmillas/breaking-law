"""
Matters router for the legal platform.

Provides CRUD operations for legal matters/cases with tenant isolation,
client linkage, and optional RBAC enforcement.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_db_session,
    get_tenant_session,
    get_current_user,
    UserContext,
    require_role,
)
from breaking_law.infra.models import Matter, Client
from breaking_law.domain.schemas.crm import MatterCreate, MatterUpdate, MatterOut

router = APIRouter(
    prefix="/matters",
    tags=["matters"],
)


def _serialize_matter(matter: Matter) -> MatterOut:
    """Convert ORM Matter to response model."""
    return MatterOut(
        id=matter.id,
        law_firm_id=matter.law_firm_id,
        client_id=matter.client_id,
        title=matter.title,
        description=matter.description,
        status=matter.status,
        created_at=matter.created_at.isoformat(),
        updated_at=matter.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=MatterOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_matter(
    data: MatterCreate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Create a new matter for a client within the current law firm."""
    # Verify the client exists and belongs to the same law firm
    client_result = await db.execute(
        select(Client).where(
            Client.id == data.client_id,
            Client.law_firm_id == current_user.law_firm_id,
        )
    )
    if client_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=400, detail="Client not found or does not belong to your law firm"
        )

    matter = Matter(
        law_firm_id=current_user.law_firm_id,
        client_id=data.client_id,
        title=data.title,
        description=data.description,
        status=data.status,
    )
    db.add(matter)
    await db.flush()
    await db.refresh(matter)
    return _serialize_matter(matter)


@router.get("/{matter_id}", response_model=MatterOut)
async def get_matter(
    matter_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Get a matter by ID (tenant-scoped)."""
    result = await db.execute(
        select(Matter).where(
            Matter.id == matter_id,
            Matter.law_firm_id == current_user.law_firm_id,
        )
    )
    matter = result.scalar_one_or_none()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    return _serialize_matter(matter)


@router.get("/", response_model=List[MatterOut])
async def list_matters(
    client_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List matters for the current law firm, optionally filtered by client."""
    stmt = (
        select(Matter)
        .where(Matter.law_firm_id == current_user.law_firm_id)
        .order_by(Matter.created_at.desc())
    )
    if client_id:
        stmt = stmt.where(Matter.client_id == client_id)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    matters = result.scalars().all()
    return [_serialize_matter(m) for m in matters]


@router.put("/{matter_id}", response_model=MatterOut)
async def update_matter(
    matter_id: uuid.UUID,
    data: MatterUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Update an existing matter (tenant-scoped)."""
    result = await db.execute(
        select(Matter).where(
            Matter.id == matter_id,
            Matter.law_firm_id == current_user.law_firm_id,
        )
    )
    matter = result.scalar_one_or_none()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    # If client_id is being updated, verify the new client belongs to the same firm
    if data.client_id is not None:
        client_result = await db.execute(
            select(Client).where(
                Client.id == data.client_id,
                Client.law_firm_id == current_user.law_firm_id,
            )
        )
        if client_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=400,
                detail="New client not found or does not belong to your law firm",
            )
        matter.client_id = data.client_id

    if data.title is not None:
        matter.title = data.title
    if data.description is not None:
        matter.description = data.description
    if data.status is not None:
        matter.status = data.status

    await db.flush()
    await db.refresh(matter)
    return _serialize_matter(matter)


@router.delete("/{matter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_matter(
    matter_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(require_role(["owner", "lawyer"])),
):
    """Delete a matter (restricted to owner or lawyer roles)."""
    result = await db.execute(
        select(Matter).where(
            Matter.id == matter_id,
            Matter.law_firm_id == current_user.law_firm_id,
        )
    )
    matter = result.scalar_one_or_none()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    await db.delete(matter)
    await db.flush()
    return None
