"""
Clients router for the legal platform.

Provides CRUD operations for law firm clients with tenant isolation
and optional RBAC enforcement.
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
from breaking_law.infra.models import Client
from breaking_law.domain.schemas.crm import ClientCreate, ClientUpdate, ClientOut

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)


def _serialize_client(client: Client) -> ClientOut:
    """Convert ORM Client to response model."""
    return ClientOut(
        id=client.id,
        law_firm_id=client.law_firm_id,
        name=client.name,
        email=client.email,
        phone=client.phone,
        created_at=client.created_at.isoformat(),
        updated_at=client.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ClientOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    data: ClientCreate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Create a new client for the current law firm."""
    client = Client(
        law_firm_id=current_user.law_firm_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return _serialize_client(client)


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Get a client by ID (tenant-scoped)."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.law_firm_id == current_user.law_firm_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return _serialize_client(client)


@router.get("/", response_model=List[ClientOut])
async def list_clients(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List all clients for the current law firm with pagination."""
    result = await db.execute(
        select(Client)
        .where(Client.law_firm_id == current_user.law_firm_id)
        .order_by(Client.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    clients = result.scalars().all()
    return [_serialize_client(c) for c in clients]


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: uuid.UUID,
    data: ClientUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Update an existing client (tenant-scoped)."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.law_firm_id == current_user.law_firm_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if data.name is not None:
        client.name = data.name
    if data.email is not None:
        client.email = data.email
    if data.phone is not None:
        client.phone = data.phone

    await db.flush()
    await db.refresh(client)
    return _serialize_client(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(require_role(["owner", "lawyer"])),
):
    """Delete a client (restricted to owner or lawyer roles)."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.law_firm_id == current_user.law_firm_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)
    await db.flush()
    return None
