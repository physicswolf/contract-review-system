from __future__ import annotations

import json
from pathlib import Path

from src.config import Settings
from src.services import llm_classifier


def test_extract_preamble_prefers_preamble_node(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "file-001",
        {
            "contract_structure": {
                "kind": "root",
                "content": [{"text": "根节点正文"}],
                "children": [
                    {
                        "kind": "preamble",
                        "content": [
                            {"text": "采购合同"},
                            {"text": "甲方：华城数字建设有限公司"},
                            {"text": "乙方：云启科技有限公司"},
                        ],
                    }
                ],
            }
        },
    )

    preamble = llm_classifier._extract_preamble("file-001", settings)

    assert preamble == "采购合同\n甲方：华城数字建设有限公司\n乙方：云启科技有限公司"


def test_extract_preamble_falls_back_to_root_content(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "file-002",
        {
            "contract_structure": {
                "kind": "root",
                "content": [
                    {"text": "服务合同"},
                    {"text": "甲方：华城数字建设有限公司"},
                ],
                "children": [],
            }
        },
    )

    preamble = llm_classifier._extract_preamble("file-002", settings)

    assert preamble == "服务合同\n甲方：华城数字建设有限公司"


def test_classify_contract_type_calls_llm_and_validates_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = make_settings(tmp_path, llm_classify_timeout=3)
    write_document(
        settings,
        "file-003",
        {
            "contract_structure": {
                "kind": "root",
                "children": [
                    {
                        "kind": "preamble",
                        "content": [
                            {"text": "智慧园区软件采购合同"},
                            {"text": "甲方：华城数字建设有限公司"},
                        ],
                    }
                ],
            }
        },
    )
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse("采购合同")

    monkeypatch.setattr(llm_classifier, "get_settings", lambda: settings)
    monkeypatch.setattr(
        llm_classifier.contract_type_repository,
        "find_all",
        lambda filters: [{"name": "采购合同"}, {"name": "服务合同"}],
    )
    monkeypatch.setattr(llm_classifier.httpx, "post", fake_post)

    result = llm_classifier.classify_contract_type("file-003")

    assert result == ("采购合同", 96)
    assert captured["url"] == "http://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["timeout"] == 3
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["temperature"] == 0
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][1]["role"] == "user"
    assert "智慧园区软件采购合同" in captured["json"]["messages"][1]["content"]
    assert "- 采购合同" in captured["json"]["messages"][1]["content"]


def test_classify_contract_type_returns_none_for_unlisted_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "file-004",
        {
            "contract_structure": {
                "kind": "root",
                "content": [{"text": "项目合作框架文本"}],
                "children": [],
            }
        },
    )

    monkeypatch.setattr(llm_classifier, "get_settings", lambda: settings)
    monkeypatch.setattr(
        llm_classifier.contract_type_repository,
        "find_all",
        lambda filters: [{"name": "采购合同"}, {"name": "服务合同"}],
    )
    monkeypatch.setattr(llm_classifier.httpx, "post", lambda *args, **kwargs: FakeResponse("其他合同"))

    assert llm_classifier.classify_contract_type("file-004") is None


def test_classify_contract_type_skips_llm_when_url_blank(monkeypatch) -> None:
    settings = make_settings(Path("/tmp"), llm_api_url="")
    monkeypatch.setattr(llm_classifier, "get_settings", lambda: settings)
    monkeypatch.setattr(
        llm_classifier.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call llm")),
    )

    assert llm_classifier.classify_contract_type("unused") is None


class FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


def make_settings(
    tmp_path: Path,
    *,
    llm_api_url: str = "http://llm.example/v1/chat/completions",
    llm_classify_timeout: int = 10,
) -> Settings:
    return Settings(
        parsing_dir=tmp_path / "parsing",
        llm_api_url=llm_api_url,
        llm_api_key="test-key",
        llm_model_name="test-model",
        llm_classify_timeout=llm_classify_timeout,
    )


def write_document(settings: Settings, file_id: str, document: dict) -> None:
    document_dir = settings.parsing_root / file_id
    document_dir.mkdir(parents=True, exist_ok=True)
    (document_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False),
        encoding="utf-8",
    )
