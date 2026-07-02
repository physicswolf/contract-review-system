from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.main import app


@pytest.fixture(autouse=True)
def isolated_parsing_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    monkeypatch.setenv("PARSING_DIR", str(tmp_path / "parsing"))
    get_settings.cache_clear()
    yield tmp_path / "parsing"
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_document_info_and_structure_endpoints(
    isolated_parsing_dir: Path,
    auth_headers: dict[str, str],
) -> None:
    file_id = "doc-001"
    document = sample_document(file_id)
    write_document(isolated_parsing_dir, file_id, document)

    async with make_client() as client:
        info_response = await client.get(f"/api/documents/{file_id}", headers=auth_headers)
        structure_response = await client.get(
            f"/api/documents/{file_id}/structure",
            headers=auth_headers,
        )

    assert info_response.status_code == 200
    assert info_response.json()["document"] == {
        "file_id": file_id,
        "schema_name": "PythonDocxContractDocument",
        "origin": {
            "filename": "采购合同.docx",
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        "has_structure": True,
        "chapter_count": 1,
        "warning_count": 1,
    }
    assert structure_response.status_code == 200
    assert structure_response.json()["structure"] == document["contract_structure"]


@pytest.mark.anyio
async def test_structure_endpoint_prefers_blocks_json(
    isolated_parsing_dir: Path,
    auth_headers: dict[str, str],
) -> None:
    file_id = "doc-blocks"
    document = sample_document(file_id)
    document["contract_structure"]["children"][0]["title"] = "旧结构标题"
    write_document(isolated_parsing_dir, file_id, document)
    write_blocks(
        isolated_parsing_dir,
        file_id,
        {
            "total_pages": 2,
            "blocks": [
                {
                    "no": 1,
                    "page": 2,
                    "text": "第一章 Blocks总则",
                    "kind": "chapter",
                    "rank": 0,
                    "bbox": {"x": 10, "y": 20, "width": 100, "height": 12},
                },
                {
                    "no": 2,
                    "page": 2,
                    "text": "第一条 Blocks标的",
                    "kind": "article",
                    "rank": 10,
                    "bbox": {"x": 12, "y": 48, "width": 120, "height": 14},
                },
                {
                    "no": 3,
                    "page": 2,
                    "text": "验收后付款。",
                    "kind": None,
                    "rank": None,
                    "bbox": {"x": 16, "y": 76, "width": 160, "height": 16},
                },
            ],
        },
    )

    async with make_client() as client:
        info_response = await client.get(f"/api/documents/{file_id}", headers=auth_headers)
        structure_response = await client.get(
            f"/api/documents/{file_id}/structure",
            headers=auth_headers,
        )

    assert info_response.status_code == 200
    assert info_response.json()["document"]["chapter_count"] == 1
    assert info_response.json()["document"]["warning_count"] == 0
    assert structure_response.status_code == 200

    structure = structure_response.json()["structure"]
    chapter = structure["children"][0]
    article = chapter["children"][0]
    assert chapter["title"] == "Blocks总则"
    assert chapter["source_ref"] == "#/blocks/0"
    assert chapter["bbox"] == [10.0, 20.0, 110.0, 32.0]
    assert article["title"] == "Blocks标的"
    assert article["source_ref"] == "#/blocks/1"
    assert article["content"][0] == {
        "source_ref": "#/blocks/2",
        "page_no": 2,
        "line_index": 3,
        "text": "验收后付款。",
        "bbox": {"l": 16.0, "t": 76.0, "r": 176.0, "b": 92.0},
    }

    edited_structure = copy.deepcopy(structure)
    edited_structure["children"][0]["title"] = "手工修订总则"

    async with make_client() as client:
        save_response = await client.put(
            f"/api/documents/{file_id}/structure",
            json={"structure": edited_structure},
            headers=auth_headers,
        )
        reloaded_response = await client.get(
            f"/api/documents/{file_id}/structure",
            headers=auth_headers,
        )

    assert save_response.status_code == 200
    assert reloaded_response.status_code == 200
    assert reloaded_response.json()["structure"]["children"][0]["title"] == "手工修订总则"
    assert read_document(isolated_parsing_dir, file_id)["contract_structure_editor"] == {
        "source": "manual"
    }


@pytest.mark.anyio
async def test_update_structure_preserves_other_document_fields(
    isolated_parsing_dir: Path,
    auth_headers: dict[str, str],
) -> None:
    file_id = "doc-002"
    document = sample_document(file_id)
    write_document(isolated_parsing_dir, file_id, document)
    updated_structure = copy.deepcopy(document["contract_structure"])
    updated_structure["children"][0]["title"] = "修订后的协议总则"
    updated_structure["children"][0]["content"][0]["text"] = "修订后的正文"

    async with make_client() as client:
        response = await client.put(
            f"/api/documents/{file_id}/structure",
            json={"structure": updated_structure},
            headers=auth_headers,
        )

    saved = read_document(isolated_parsing_dir, file_id)
    assert response.status_code == 200
    assert response.json() == {"message": "结构已保存"}
    assert saved["texts"] == document["texts"]
    assert saved["tables"] == document["tables"]
    assert saved["contract_structure"]["children"][0]["source_ref"] == "#/texts/1"
    assert saved["contract_structure"]["children"][0]["content"][0]["source_ref"] == "#/texts/2"
    assert saved["contract_structure"]["children"][0]["title"] == "修订后的协议总则"
    assert not (isolated_parsing_dir / file_id / "document.json.part").exists()


@pytest.mark.anyio
async def test_update_structure_rejects_duplicate_node_id(
    isolated_parsing_dir: Path,
    auth_headers: dict[str, str],
) -> None:
    file_id = "doc-003"
    document = sample_document(file_id)
    write_document(isolated_parsing_dir, file_id, document)
    bad_structure = copy.deepcopy(document["contract_structure"])
    bad_structure["children"].append(copy.deepcopy(bad_structure["children"][0]))

    async with make_client() as client:
        response = await client.put(
            f"/api/documents/{file_id}/structure",
            json={"structure": bad_structure},
            headers=auth_headers,
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "node_id 重复：node_0001"}


@pytest.mark.anyio
async def test_missing_document_returns_standard_error(auth_headers: dict[str, str]) -> None:
    async with make_client() as client:
        response = await client.get("/api/documents/missing", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "文档不存在或尚未解析完成"}


def write_document(parsing_dir: Path, file_id: str, document: dict[str, Any]) -> None:
    document_dir = parsing_dir / file_id
    document_dir.mkdir(parents=True, exist_ok=True)
    (document_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_blocks(parsing_dir: Path, file_id: str, blocks: dict[str, Any]) -> None:
    document_dir = parsing_dir / file_id
    document_dir.mkdir(parents=True, exist_ok=True)
    (document_dir / "blocks.json").write_text(
        json.dumps(blocks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_document(parsing_dir: Path, file_id: str) -> dict[str, Any]:
    return json.loads((parsing_dir / file_id / "document.json").read_text("utf-8"))


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def sample_document(file_id: str) -> dict[str, Any]:
    return {
        "schema_name": "PythonDocxContractDocument",
        "version": "1.0",
        "name": file_id,
        "origin": {
            "filename": "采购合同.docx",
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        "texts": [{"self_ref": "#/texts/1", "text": "第一章 协议总则"}],
        "tables": [{"self_ref": "#/tables/1"}],
        "warnings": [{"message": "示例告警"}],
        "contract_structure": {
            "node_id": "root",
            "parent_id": None,
            "label": "",
            "title": "ROOT",
            "kind": "root",
            "rank": -1,
            "path": [],
            "children": [
                {
                    "node_id": "node_0001",
                    "parent_id": "root",
                    "label": "第一章",
                    "title": "协议总则",
                    "kind": "chapter",
                    "rank": 0,
                    "path": [],
                    "source": "literal",
                    "raw_text": "第一章 协议总则",
                    "source_ref": "#/texts/1",
                    "page_no": 1,
                    "line_index": 0,
                    "tree_depth": 1,
                    "content": [
                        {
                            "source_ref": "#/texts/2",
                            "text": "本章约定协议基本规则。",
                        }
                    ],
                    "tables": [],
                    "warnings": [],
                    "children": [],
                }
            ],
        },
    }
