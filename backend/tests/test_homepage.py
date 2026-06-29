from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.anyio
async def test_health_check() -> None:
    async with make_client() as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0"}


@pytest.mark.anyio
async def test_protected_api_requires_login() -> None:
    async with make_client() as client:
        response = await client.get("/api/contracts")

    assert response.status_code == 401
    assert response.json() == {"detail": "未登录"}


@pytest.mark.anyio
async def test_review_purposes_api(auth_headers: dict[str, str]) -> None:
    async with make_client() as client:
        response = await client.get("/api/review/purposes", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert [item["name"] for item in payload["items"]] == [
        "条款完整性",
        "风险识别",
        "合规性检查",
        "权责对等",
    ]


@pytest.mark.anyio
async def test_internal_api_uses_tmp_error_without_jwt() -> None:
    async with make_client() as client:
        response = await client.get("/api/internal/contract-types/match")

    assert response.status_code == 400
    assert response.json() == {"code": 40001, "msg": "name 和 stance 不能为空"}


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
