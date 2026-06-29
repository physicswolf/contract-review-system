from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.services.contract_extractor import extract_contract_meta


def test_docling_page_one_heading_title_overrides_filename(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "docling-001",
        {
            "origin": {"filename": "扫描件001.pdf", "mimetype": "application/pdf"},
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "label": "section_header",
                    "text": "智慧园区软件采购合同",
                    "prov": [{"page_no": 1, "bbox": {}}],
                },
                {
                    "self_ref": "#/texts/1",
                    "label": "text",
                    "text": "甲方：华城数字建设有限公司",
                    "prov": [{"page_no": 1}],
                },
            ],
            "contract_structure": empty_structure(),
        },
    )

    meta = extract_contract_meta("docling-001", settings)

    assert meta["contract_name"] == "智慧园区软件采购合同"


def test_pymupdf_page_two_heading_beats_page_one_body_text(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "pymupdf-001",
        {
            "origin": {"filename": "合同最终版_v3.pdf", "mimetype": "application/pdf"},
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "label": "text",
                    "text": "本合同由双方根据项目背景共同签署",
                    "prov": [{"page_no": 1, "source_ref": "#/pages/0/lines/0"}],
                },
                {
                    "self_ref": "#/texts/1",
                    "label": "section_header",
                    "text": "智慧园区软件采购合同",
                    "prov": [{"page_no": 2, "source_ref": "#/pages/1/lines/0"}],
                },
            ],
            "contract_structure": empty_structure(),
        },
    )

    meta = extract_contract_meta("pymupdf-001", settings)

    assert meta["contract_name"] == "智慧园区软件采购合同"


def test_python_docx_heading_without_page_number(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "docx-001",
        {
            "origin": {
                "filename": "合同最终版_v3.docx",
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "label": "section_header",
                    "text": "服务合同",
                    "prov": [{"paragraph_index": 0}],
                },
                {
                    "self_ref": "#/texts/1",
                    "label": "section_header",
                    "text": "IT 基础设施服务合同",
                    "prov": [{"paragraph_index": 1}],
                },
            ],
            "contract_structure": empty_structure(),
        },
    )

    meta = extract_contract_meta("docx-001", settings)

    assert meta["contract_name"] == "IT 基础设施服务合同"


def test_docx_cover_title_beats_late_clause_section_headers(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "932477e7-a67e-44f8-85a5-ad1ba591c559",
        {
            "origin": {
                "filename": "932477e7-a67e-44f8-85a5-ad1ba591c559.docx",
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "label": "text",
                    "text": "大数据应用系统及数据灾备系统平台开发项目服务合同",
                    "prov": [{"paragraph_index": 2}],
                },
                {
                    "self_ref": "#/texts/1",
                    "label": "text",
                    "text": "项目名称：大数据应用系统及数据灾备系统平台开发项目服务合同",
                    "prov": [{"paragraph_index": 4}],
                },
                {
                    "self_ref": "#/texts/2",
                    "label": "section_header",
                    "text": "第二章 合同价款及支付方式",
                    "prov": [{"paragraph_index": 36}],
                },
                {
                    "self_ref": "#/texts/3",
                    "label": "section_header",
                    "text": "6.4 检验不合格的，乙方应无条件修改、优化直至检测合格，否则甲方有权解除合同",
                    "prov": [{"paragraph_index": 155}],
                },
                {
                    "self_ref": "#/texts/4",
                    "label": "section_header",
                    "text": (
                        "按照国家相关法律法规，需对本项目软件及系统平台等相关内容，"
                        "依据招投标文件、设计方案、技术标准、规范等要求，通过第三方"
                        "具有相关资质测试机构的检测，该费用已包含在该签约合同价中。"
                    ),
                    "prov": [{"paragraph_index": 156}],
                },
            ],
            "contract_structure": empty_structure(),
        },
    )

    meta = extract_contract_meta(
        "932477e7-a67e-44f8-85a5-ad1ba591c559",
        settings,
    )

    assert meta["contract_name"] == "大数据应用系统及数据灾备系统平台开发项目服务合同"


def test_title_extraction_falls_back_to_filename(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_document(
        settings,
        "fallback-001",
        {
            "origin": {"filename": "合同.pdf", "mimetype": "application/pdf"},
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "label": "section_header",
                    "text": "项目说明书",
                    "prov": [{"page_no": 1}],
                }
            ],
            "contract_structure": empty_structure(),
        },
    )

    meta = extract_contract_meta("fallback-001", settings)

    assert meta["contract_name"] == "合同"


def make_settings(tmp_path: Path) -> Settings:
    return Settings(parsing_dir=tmp_path / "parsing")


def write_document(settings: Settings, file_id: str, document: dict[str, Any]) -> None:
    document_dir = settings.parsing_root / file_id
    document_dir.mkdir(parents=True, exist_ok=True)
    (document_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def empty_structure() -> dict[str, Any]:
    return {"node_id": "root", "children": []}
