from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.main import app
from src.services.contract_store import ContractRepository
from tests.fakes import InMemoryContractRepository


@pytest.fixture
def contract_repo(monkeypatch: pytest.MonkeyPatch) -> InMemoryContractRepository:
    repo = InMemoryContractRepository()
    monkeypatch.setattr(
        "src.api.contracts.get_contract_repository",
        lambda settings=None: repo,
    )
    monkeypatch.setattr(
        "src.services.contract_store.get_contract_repository",
        lambda settings=None: repo,
    )
    return repo


@pytest.fixture(autouse=True)
def isolated_contract_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contract_repo: InMemoryContractRepository,
) -> Iterator[dict[str, Path]]:
    paths = {
        "uploads": tmp_path / "uploads",
        "parsing": tmp_path / "parsing",
    }
    monkeypatch.setenv("UPLOAD_DIR", str(paths["uploads"]))
    monkeypatch.setenv("PARSING_DIR", str(paths["parsing"]))
    get_settings.cache_clear()
    contract_repo.initialize()
    yield paths
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_list_contracts_supports_filters(
    contract_repo: InMemoryContractRepository,
    auth_headers: dict[str, str],
) -> None:
    repo = contract_repo
    insert_contract(
        repo,
        file_id="file-001",
        contract_name="智慧园区软件采购合同",
        party_a="华城数字建设有限公司",
        party_b="云启科技有限公司",
        contract_type="采购合同",
        review_time="2026-06-25T10:20:00+08:00",
    )
    insert_contract(
        repo,
        file_id="file-002",
        contract_name="年度技术服务框架协议",
        party_a="远航实业集团",
        party_b="新程信息技术有限公司",
        contract_type="服务合同",
        review_time="2026-06-25T09:24:00+08:00",
    )

    async with make_client() as client:
        all_response = await client.get("/api/contracts", headers=auth_headers)
        filtered_response = await client.get(
            "/api/contracts",
            params={"name": "技术", "partyB": "新程"},
            headers=auth_headers,
        )
        type_response = await client.get(
            "/api/contracts",
            params={"contract_type": "采购"},
            headers=auth_headers,
        )

    assert all_response.status_code == 200
    all_payload = all_response.json()
    assert all_payload["total"] == 2
    assert all_payload["items"][0]["name"] == "智慧园区软件采购合同"

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["total"] == 1
    assert filtered_payload["items"][0]["id"] == "2"

    assert type_response.status_code == 200
    type_payload = type_response.json()
    assert type_payload["total"] == 1
    assert type_payload["items"][0]["id"] == "1"


@pytest.mark.anyio
async def test_create_and_update_contract_record(auth_headers: dict[str, str]) -> None:
    async with make_client() as client:
        create_response = await client.post(
            "/api/contracts",
            json={
                "fileId": "manual-001",
                "name": "手工合同",
                "partyA": "甲方",
                "partyB": "乙方",
                "type": "服务合同",
                "reviewTime": "2026-06-27T10:00:00+08:00",
            },
            headers=auth_headers,
        )
        contract_id = create_response.json()["id"]
        update_response = await client.put(
            f"/api/contracts/{contract_id}",
            json={"name": "更新后的手工合同", "partyB": "新乙方"},
            headers=auth_headers,
        )

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "手工合同"
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "更新后的手工合同"
    assert updated["partyB"] == "新乙方"


@pytest.mark.anyio
async def test_delete_contract_removes_database_record_and_files(
    isolated_contract_state: dict[str, Path],
    contract_repo: InMemoryContractRepository,
    auth_headers: dict[str, str],
) -> None:
    file_id = "file-004"
    repo = contract_repo
    contract_id = insert_contract(repo, file_id=file_id)
    upload_dir = isolated_contract_state["uploads"] / "2026" / "06" / "25"
    upload_dir.mkdir(parents=True)
    upload_file = upload_dir / f"{file_id}.pdf"
    metadata_file = upload_dir / f"{file_id}.json"
    upload_file.write_bytes(valid_pdf())
    metadata_file.write_text("{}", encoding="utf-8")
    parsing_dir = isolated_contract_state["parsing"] / file_id
    parsing_dir.mkdir(parents=True)
    (parsing_dir / "document.json").write_text("{}", encoding="utf-8")

    async with make_client() as client:
        response = await client.delete(f"/api/contracts/{contract_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert repo.find_by_id(contract_id) is None
    assert not upload_file.exists()
    assert not metadata_file.exists()
    assert not parsing_dir.exists()


@pytest.mark.anyio
async def test_missing_contract_returns_standard_error(auth_headers: dict[str, str]) -> None:
    async with make_client() as client:
        response = await client.delete("/api/contracts/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "合同不存在"}


def insert_contract(
    repo: ContractRepository,
    *,
    file_id: str,
    contract_name: str = "测试合同",
    party_a: str = "甲方公司",
    party_b: str = "乙方公司",
    contract_type: str = "未分类",
    review_time: str = "2026-06-25T08:00:00+08:00",
) -> int:
    return repo.upsert_by_file_id(
        {
            "file_id": file_id,
            "contract_name": contract_name,
            "party_a": party_a,
            "party_b": party_b,
            "contract_type": contract_type,
            "review_time": review_time,
            "created_at": review_time,
            "updated_at": review_time,
        }
    )


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def valid_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"
