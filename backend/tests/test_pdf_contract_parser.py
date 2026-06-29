import sys
from types import SimpleNamespace

from src.services.contract_structure_parser import StandardLine, parse_contract_structure_from_lines
from src.services.pdf_contract_parser import (
    add_contract_structure_to_docling_pdf_json_data,
    parse_pymupdf4llm_pdf_to_json_data,
    standard_lines_from_docling_json_data,
)


def test_shared_structure_parser_skips_cover_toc_page_numbers_and_tables():
    lines = [
        StandardLine("合同封面", "#/lines/0", page_no=1, line_index=0, line_count=1),
        StandardLine("目录", "#/lines/1", page_no=2, line_index=0, line_count=2),
        StandardLine(
            "第一部分 专用条款................1",
            "#/lines/2",
            page_no=2,
            line_index=1,
            line_count=2,
        ),
        StandardLine("1", "#/lines/3", page_no=3, line_index=0, line_count=4),
        StandardLine("第一部分 专用条款", "#/lines/4", page_no=3, line_index=1, line_count=4),
        StandardLine("一、工程概况", "#/lines/5", page_no=3, line_index=2, line_count=4),
        StandardLine("| 1 | 货物 |", "#/lines/6", page_no=3, line_index=3, line_count=4),
    ]

    structure, warnings = parse_contract_structure_from_lines(lines)

    preamble = structure["children"][0]
    first_part = structure["children"][1]
    assert preamble["kind"] == "preamble"
    assert preamble["title"] == "合同首部"
    assert preamble["content"][0]["text"] == "合同封面"
    assert first_part["label"] == "第一部分"
    assert first_part["children"][0]["label"] == "一、"
    assert first_part["children"][0]["tables"][0]["text"] == "| 1 | 货物 |"
    assert warnings == []


def test_shared_structure_parser_removes_empty_duplicate_chapters():
    lines = [
        StandardLine("第一章 协议总则", "#/lines/0", page_no=1),
        StandardLine("第二章 专用条款", "#/lines/1", page_no=1),
        StandardLine("第一章 协议总则", "#/lines/2", page_no=2),
        StandardLine("本章正文", "#/lines/3", page_no=2),
        StandardLine("第二章 专用条款", "#/lines/4", page_no=3),
        StandardLine("专用条款正文", "#/lines/5", page_no=3),
    ]

    structure, warnings = parse_contract_structure_from_lines(lines)

    children = structure["children"]
    assert [child["label"] for child in children] == ["第一章", "第二章"]
    assert children[0]["content"][0]["text"] == "本章正文"
    assert children[1]["content"][0]["text"] == "专用条款正文"
    assert warnings == []


def test_add_contract_structure_to_docling_pdf_json_data():
    payload = add_contract_structure_to_docling_pdf_json_data(
        {
            "schema_name": "DoclingDocument",
            "texts": [
                {"self_ref": "#/texts/0", "text": "封面", "prov": [{"page_no": 1}]},
                {
                    "self_ref": "#/texts/1",
                    "text": "第一部分 专用条款",
                    "label": "section_header",
                    "prov": [{"page_no": 2}],
                },
                {
                    "self_ref": "#/texts/2",
                    "text": "一、工程概况",
                    "label": "section_header",
                    "prov": [{"page_no": 2}],
                },
            ],
        },
        source_file="contract.pdf",
        doc_id="file-uuid",
    )

    children = payload["contract_structure"]["children"]
    assert children[0]["kind"] == "preamble"
    assert children[0]["content"][0]["text"] == "封面"
    assert children[1]["label"] == "第一部分"
    assert children[1]["children"][0]["label"] == "一、"
    assert payload["contract_structure_parser"]["source"] == "docling"


def test_docling_structure_uses_orig_to_recover_split_dotted_numbering():
    payload = add_contract_structure_to_docling_pdf_json_data(
        {
            "schema_name": "DoclingDocument",
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "text": "第一章 协议总则",
                    "label": "section_header",
                    "prov": [{"page_no": 1}],
                },
                {
                    "self_ref": "#/texts/1",
                    "text": "2. 合同标的",
                    "label": "list_item",
                    "prov": [{"page_no": 1}],
                },
                {
                    "self_ref": "#/texts/2",
                    "orig": "2. 1 货物名称： 液位仪及测漏传感器",
                    "text": "1 货物名称： 液位仪及测漏传感器",
                    "label": "list_item",
                    "prov": [{"page_no": 1}],
                },
            ],
        },
        source_file="contract.pdf",
        doc_id="file-uuid",
    )

    chapter = payload["contract_structure"]["children"][0]
    arabic = chapter["children"][0]
    dotted = arabic["children"][0]
    assert chapter["label"] == "第一章"
    assert arabic["label"] == "2."
    assert dotted["label"] == "2.1"
    assert dotted["raw_text"].startswith("2.1 货物名称")


def test_docling_structure_merges_same_visual_line_text_items():
    lines = standard_lines_from_docling_json_data(
        {
            "schema_name": "DoclingDocument",
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "text": "第一",
                    "label": "text",
                    "parent": {"$ref": "#/groups/1"},
                    "prov": [
                        {
                            "page_no": 1,
                            "bbox": {"l": 100, "t": 200, "r": 120, "b": 190},
                        }
                    ],
                },
                {
                    "self_ref": "#/texts/1",
                    "text": "章： 协议总则",
                    "label": "text",
                    "parent": {"$ref": "#/groups/1"},
                    "prov": [
                        {
                            "page_no": 1,
                            "bbox": {"l": 120.2, "t": 200, "r": 180, "b": 190},
                        }
                    ],
                },
            ],
        }
    )

    assert len(lines) == 1
    assert lines[0].text == "第一章: 协议总则"


def test_docling_plain_text_chapter_reference_is_not_top_level_heading():
    payload = add_contract_structure_to_docling_pdf_json_data(
        {
            "schema_name": "DoclingDocument",
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "text": "第一章 协议总则",
                    "label": "section_header",
                    "prov": [{"page_no": 1}],
                },
                {
                    "self_ref": "#/texts/1",
                    "text": "第一章： 协议总则",
                    "label": "text",
                    "prov": [{"page_no": 1}],
                },
                {
                    "self_ref": "#/texts/2",
                    "text": "第二章： 专用条款",
                    "label": "text",
                    "prov": [{"page_no": 1}],
                },
            ],
        },
        source_file="contract.pdf",
        doc_id="file-uuid",
    )

    children = payload["contract_structure"]["children"]
    assert [child["label"] for child in children] == ["第一章"]
    assert [item["text"] for item in children[0]["content"]] == [
        "第一章: 协议总则第二章: 专用条款"
    ]


def test_parse_pymupdf4llm_pdf_to_json_data_uses_markdown_chunks(tmp_path, monkeypatch):
    pdf_path = tmp_path / "contract.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")

    fake_module = SimpleNamespace(
        __version__="test-version",
        to_markdown=lambda path, **kwargs: [
            {
                "metadata": {"page_number": 1},
                "text": "封面\n目录\n第一部分 专用条款\n",
            },
            {
                "metadata": {"page_number": 2},
                "text": "第一部分 专用条款\n一、工程概况\n| 1 | 货物 |\n",
            }
        ],
    )
    monkeypatch.setitem(sys.modules, "pymupdf4llm", fake_module)

    payload = parse_pymupdf4llm_pdf_to_json_data(pdf_path, doc_id="file-uuid")

    assert payload["schema_name"] == "PyMuPDF4LLMContractDocument"
    assert payload["parser"]["pymupdf4llm"] == "test-version"
    assert payload["contract_structure"]["children"][0]["kind"] == "preamble"
    assert payload["contract_structure"]["children"][1]["label"] == "第一部分"
    assert payload["tables"][0]["text"] == "| 1 | 货物 |"
