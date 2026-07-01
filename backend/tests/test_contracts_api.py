from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

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
async def test_start_audit_from_upload_creates_contract_when_review_starts(
    isolated_contract_state: dict[str, Path],
    contract_repo: InMemoryContractRepository,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    file_id = "file-audit"
    parsing_dir = isolated_contract_state["parsing"] / file_id
    parsing_dir.mkdir(parents=True)
    (parsing_dir / "document.json").write_text(
        json.dumps(
            {
                "origin": {"filename": "技术服务合同.docx"},
                "texts": [
                    {
                        "text": "技术服务合同",
                        "label": "title",
                        "prov": [{"paragraph_index": 0}],
                    }
                ],
                "contract_structure": {
                    "node_id": "root",
                    "kind": "root",
                    "title": "ROOT",
                    "content": [
                        {
                            "text": "甲方：华城数字建设有限公司\n乙方：云启科技有限公司"
                        },
                        {"text": "付款期限应在验收后九十日内完成。"},
                    ],
                    "children": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fake_store = FakeAuditResultStore()
    monkeypatch.setattr("src.api.contracts.audit_result_store", fake_store)
    monkeypatch.setattr(
        "src.api.contracts.audit_point_repository.find_by_id",
        lambda point_id: fake_audit_point() if point_id == 1 else None,
    )

    assert contract_repo.count() == 0

    async with make_client() as client:
        response = await client.post(
            "/api/contracts/audit",
            json={
                "fileId": file_id,
                "role": "甲方",
                "points": [1],
                "contractType": "服务合同",
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert contract_repo.count() == 1
    record = contract_repo.find_by_id(int(payload["id"]))
    assert record is not None
    assert record["file_id"] == file_id
    assert record["contract_name"] == "技术服务合同"
    assert record["party_a"] == "华城数字建设有限公司"
    assert record["party_b"] == "云启科技有限公司"
    assert record["contract_type"] == "服务合同"
    assert record["risk_count"] == 1
    assert fake_store.tasks[0]["contract_id"] == int(payload["id"])
    assert fake_store.tasks[0]["stance"] == "甲方"
    assert fake_store.results[1][0]["audit_point_id"] == 1


@pytest.mark.anyio
async def test_start_audit_from_upload_requires_parsed_document(
    contract_repo: InMemoryContractRepository,
    auth_headers: dict[str, str],
) -> None:
    async with make_client() as client:
        response = await client.post(
            "/api/contracts/audit",
            json={
                "fileId": "missing-file",
                "role": "甲方",
                "points": [1],
                "contractType": "服务合同",
            },
            headers=auth_headers,
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "文档不存在或尚未解析完成"}
    assert contract_repo.count() == 0


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


def fake_audit_point() -> dict[str, Any]:
    return {
        "id": 1,
        "dim_id": 10,
        "dim_name": "付款条款",
        "name": "付款期限",
        "description": "付款期限过长",
        "default_result": {
            "level": "major",
            "clause": "付款期限",
            "overview": "付款期限过长，存在资金周转风险。",
            "solution": "建议明确付款节点和最晚付款期限。",
        },
        "risk_points": [{"high": "付款周期过长可能影响现金流。"}],
    }


class FakeAuditResultStore:
    def __init__(self) -> None:
        self.tasks: list[dict[str, Any]] = []
        self.results: dict[int, list[dict[str, Any]]] = {}
        self.stats: dict[int, list[dict[str, Any]]] = {}

    def create_task(
        self,
        contract_id: int,
        stance: str,
        contract_type_id: int | None = None,
    ) -> int:
        task_id = len(self.tasks) + 1
        self.tasks.append(
            {
                "id": task_id,
                "contract_id": contract_id,
                "stance": stance,
                "contract_type_id": contract_type_id,
            }
        )
        return task_id

    def insert_results(self, task_id: int, items: list[dict[str, Any]]) -> None:
        self.results[task_id] = items

    def insert_stats(self, task_id: int, stats: list[dict[str, Any]]) -> None:
        self.stats[task_id] = stats

    def complete_task(
        self,
        task_id: int,
        *,
        total: int,
        major: int,
        general: int,
        status: str = "succeeded",
    ) -> None:
        self.tasks[task_id - 1].update(
            {
                "total": total,
                "major": major,
                "general": general,
                "status": status,
            }
        )
