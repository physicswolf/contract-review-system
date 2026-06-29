from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services.audit_point_store import audit_point_repository
from src.services.contract_type_store import contract_type_repository
from src.services.dimension_store import dimension_repository


@pytest.mark.anyio
async def test_dimensions_return_tmp_format(
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    monkeypatch.setattr(
        dimension_repository,
        "find_all",
        lambda enabled=None: [
            {
                "id": 1,
                "name": "基础核查",
                "description": "主体信息",
                "sort_order": 10,
                "enabled": 1,
                "updated_at": "2026-06-30T10:00:00",
            }
        ],
    )

    async with make_client() as client:
        response = await client.get("/api/dimensions", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "msg": "ok",
        "data": [
            {
                "id": 1,
                "name": "基础核查",
                "description": "主体信息",
                "desc": "主体信息",
                "sortOrder": 10,
                "enabled": 1,
                "status": "已启用",
                "updatedAt": "2026-06-30T10:00:00",
            }
        ],
    }


@pytest.mark.anyio
async def test_audit_point_toggle_requires_enabled(
    auth_headers: dict[str, str],
) -> None:
    async with make_client() as client:
        response = await client.patch(
            "/api/audit-points/1/enabled",
            json={},
            headers=auth_headers,
        )

    assert response.status_code == 400
    assert response.json() == {"code": 40001, "msg": "enabled 不能为空"}


@pytest.mark.anyio
async def test_contract_type_save_audit_points(
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    saved: dict[str, object] = {}

    def replace_associations(type_id: int, point_ids: list[int]) -> None:
        saved["type_id"] = type_id
        saved["point_ids"] = point_ids

    monkeypatch.setattr(contract_type_repository, "replace_associations", replace_associations)

    async with make_client() as client:
        response = await client.put(
            "/api/contract-types/7/audit-points",
            json={"auditPointIds": [1, "2"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "msg": "ok"}
    assert saved == {"type_id": 7, "point_ids": [1, 2]}


@pytest.mark.anyio
async def test_internal_match_requires_name_and_stance() -> None:
    async with make_client() as client:
        response = await client.get("/api/internal/contract-types/match")

    assert response.status_code == 400
    assert response.json() == {"code": 40001, "msg": "name 和 stance 不能为空"}


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
