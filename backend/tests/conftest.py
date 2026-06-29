import pytest

from src.services.auth_service import create_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(1)}"}
