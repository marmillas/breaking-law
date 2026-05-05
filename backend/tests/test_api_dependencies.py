import pytest
import uuid
from fastapi import HTTPException
from breaking_law.api.deps import require_role, get_current_user, UserContext


@pytest.mark.asyncio
async def test_require_role_allows_allowed_roles():
    checker = require_role(["owner", "lawyer"])
    user = UserContext(
        user_id=uuid.uuid4(),
        law_firm_id=uuid.uuid4(),
        email="a@b.com",
        role="owner",
        full_name="A",
    )
    result = await checker(current_user=user)
    assert result == user


@pytest.mark.asyncio
async def test_require_role_blocks_disallowed_roles():
    checker = require_role(["owner"])
    user = UserContext(
        user_id=uuid.uuid4(),
        law_firm_id=uuid.uuid4(),
        email="a@b.com",
        role="assistant",
        full_name="A",
    )
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_raises_401_for_invalid_token():
    from unittest.mock import AsyncMock

    mock_db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="invalid.token", db=mock_db)
    assert exc_info.value.status_code == 401
