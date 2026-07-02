from __future__ import annotations

import asyncio
import json
from io import BytesIO

import pytest
from docx import Document
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.main import app


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PARSING_DIR", str(tmp_path / "parsing"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "50")
    monkeypatch.setenv("DOCX_PARSER_ENGINE", "docling")
    monkeypatch.setenv("PDF_PARSER_ENGINE", "docling")
    get_settings.cache_clear()
    yield {
        "uploads": tmp_path / "uploads",
        "parsing": tmp_path / "parsing",
    }
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def fake_document_parser(monkeypatch):
    from src.services.document_parser import ParsingArtifacts

    def parse_uploaded_document(source_path, file_id, extension, settings):
        parsing_dir = settings.parsing_root / file_id
        parsing_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = None
        if extension == ".docx":
            pdf_path = parsing_dir / "document.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
        document = {
            "texts": [
                {
                    "text": "合同",
                    "prov": [
                        {
                            "page_no": 1,
                            "line_index": 0,
                            "bbox": {"l": 10, "t": 20, "r": 110, "b": 40},
                        }
                    ],
                }
            ],
            "tables": [],
        }
        (parsing_dir / "document.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return ParsingArtifacts(
            directory=parsing_dir,
            json_path=parsing_dir / "document.json",
            pdf_path=pdf_path,
        )

    monkeypatch.setattr(
        "src.pipelines.document_tasks.parse_uploaded_document",
        parse_uploaded_document,
    )


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest.mark.anyio
async def test_upload_valid_pdf(client, isolated_upload_dir, auth_headers):
    response = await client.post(
        "/api/files/upload",
        files={"file": ("采购合同.pdf", valid_pdf(), "application/pdf")},
        headers=auth_headers,
    )

    payload = response.json()
    file_payload = payload["file"]
    task_payload = payload["task"]
    assert response.status_code == 200
    assert file_payload["original_name"] == "采购合同.pdf"
    assert file_payload["extension"] == ".pdf"
    assert file_payload["size"] == len(valid_pdf())
    assert task_payload["file_id"] == file_payload["id"]
    task = await wait_for_task(client, task_payload["id"], "succeeded", auth_headers)
    parsing_dir = isolated_upload_dir["parsing"] / file_payload["id"]
    assert task["document_json_path"] == str(parsing_dir / "document.json")
    assert (parsing_dir / "document.json").is_file()
    assert read_blocks(parsing_dir)["blocks"][0]["text"] == "合同"
    assert not (parsing_dir / "document.pdf").exists()


@pytest.mark.anyio
async def test_get_file_metadata(client, auth_headers):
    upload_response = await client.post(
        "/api/files/upload",
        files={"file": ("采购合同.pdf", valid_pdf(), "application/pdf")},
        headers=auth_headers,
    )
    file_payload = upload_response.json()["file"]

    response = await client.get(f"/api/files/{file_payload['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["file"]["original_name"] == "采购合同.pdf"


@pytest.mark.anyio
async def test_delete_upload_artifacts_removes_upload_and_parsing_files(
    client,
    isolated_upload_dir,
    auth_headers,
):
    upload_response = await client.post(
        "/api/files/upload",
        files={"file": ("采购合同.pdf", valid_pdf(), "application/pdf")},
        headers=auth_headers,
    )
    payload = upload_response.json()
    file_id = payload["file"]["id"]
    await wait_for_task(client, payload["task"]["id"], "succeeded", auth_headers)
    assert list(isolated_upload_dir["uploads"].rglob(f"{file_id}.*"))
    assert (isolated_upload_dir["parsing"] / file_id / "document.json").is_file()

    response = await client.delete(f"/api/files/{file_id}/artifacts", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert list(isolated_upload_dir["uploads"].rglob(f"{file_id}.*")) == []
    assert not (isolated_upload_dir["parsing"] / file_id).exists()


@pytest.mark.anyio
async def test_upload_valid_docx(client, isolated_upload_dir, auth_headers):
    content = valid_docx()
    response = await client.post(
        "/api/files/upload",
        files={
            "file": (
                "采购合同.docx",
                content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers=auth_headers,
    )

    payload = response.json()
    file_payload = payload["file"]
    task_payload = payload["task"]
    assert response.status_code == 200
    assert file_payload["extension"] == ".docx"
    assert file_payload["size"] == len(content)
    await wait_for_task(client, task_payload["id"], "succeeded", auth_headers)
    parsing_dir = isolated_upload_dir["parsing"] / file_payload["id"]
    assert (parsing_dir / "document.pdf").is_file()
    assert (parsing_dir / "document.json").is_file()
    assert read_blocks(parsing_dir)["blocks"][0]["bbox"] == {
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 20,
    }


@pytest.mark.anyio
async def test_missing_file_returns_standard_error(client, auth_headers):
    response = await client.post("/api/files/upload", headers=auth_headers)

    assert response.status_code == 422
    assert response.json() == {"detail": "请提交合同文件"}


@pytest.mark.anyio
async def test_signature_mismatch_is_rejected_and_temp_file_cleaned(
    client,
    isolated_upload_dir,
    auth_headers,
):
    response = await client.post(
        "/api/files/upload",
        files={"file": ("伪造合同.pdf", b"not a pdf", "application/pdf")},
        headers=auth_headers,
    )

    assert_error(response, 415, "文件内容与扩展名不匹配")
    assert list(isolated_upload_dir["uploads"].rglob("*.part")) == []
    assert list(isolated_upload_dir["uploads"].rglob("*.pdf")) == []


@pytest.mark.anyio
async def test_parse_failure_cleans_upload_and_returns_failed_task(
    client,
    isolated_upload_dir,
    monkeypatch,
    auth_headers,
):
    from src.services.document_parser import ParsingError

    def fail_parse(source_path, file_id, extension, settings):
        raise ParsingError("DOCUMENT_PARSING_ERROR")

    monkeypatch.setattr("src.pipelines.document_tasks.parse_uploaded_document", fail_parse)

    response = await client.post(
        "/api/files/upload",
        files={"file": ("采购合同.pdf", valid_pdf(), "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 200
    task = await wait_for_task(client, response.json()["task"]["id"], "failed", auth_headers)
    assert task["error"]["code"] == "DOCUMENT_PARSING_ERROR"
    assert list(isolated_upload_dir["uploads"].rglob("*.pdf")) == []
    assert list(isolated_upload_dir["uploads"].rglob("*.json")) == []


def assert_error(response, status_code, detail):
    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


async def wait_for_task(client, task_id, expected_status, headers):
    for _ in range(50):
        response = await client.get(f"/api/files/tasks/{task_id}", headers=headers)
        assert response.status_code == 200
        task = response.json()["task"]
        if task["status"] == expected_status:
            return task
        await asyncio.sleep(0.02)
    raise AssertionError(f"task {task_id} did not reach {expected_status}")


def valid_pdf():
    return b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"


def valid_docx():
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("合同")
    document.save(buffer)
    return buffer.getvalue()


def read_blocks(parsing_dir):
    return json.loads((parsing_dir / "blocks.json").read_text(encoding="utf-8"))
