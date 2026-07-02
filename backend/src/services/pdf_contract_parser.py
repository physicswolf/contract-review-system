from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from src.services.contract_structure_parser import (
    StandardLine,
    clean_contract_line,
    is_markdown_table_line,
    parse_heading_token,
    parse_contract_structure_from_lines,
    parse_number_token,
)


PYMUPDF4LLM_SCHEMA_NAME = "PyMuPDF4LLMContractDocument"
DOCLING_PDF_STRUCTURE_SCHEMA_NAME = "DoclingPDFContractDocument"
SCHEMA_VERSION = "1.0.0"
PYMUPDF4LLM_SKIPPED_BOX_CLASSES = {"picture", "formula", "page-header", "page-footer"}
PYMUPDF4LLM_BBOX_COORD_ORIGIN = "TOPLEFT"


def parse_pymupdf4llm_pdf_to_json_data(
    pdf_path: Path,
    doc_id: str | None = None,
) -> dict[str, Any]:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError(
            "pymupdf4llm is not installed. Install it before using "
            "PDF_PARSER_ENGINE=pymupdf4llm."
        ) from exc

    chunks = call_pymupdf4llm_to_markdown(pymupdf4llm, pdf_path)
    lines = standard_lines_from_pymupdf4llm_chunks(chunks)
    contract_structure, warnings = parse_contract_structure_from_lines(lines)

    return {
        "schema_name": PYMUPDF4LLM_SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "name": doc_id or pdf_path.stem,
        "origin": {
            "filename": pdf_path.name,
            "mimetype": "application/pdf",
        },
        "parser": {
            "name": "pymupdf4llm-contract-parser",
            "pymupdf4llm": getattr(pymupdf4llm, "__version__", None),
        },
        "texts": build_text_items_from_standard_lines(lines),
        "tables": build_table_items_from_standard_lines(lines),
        "contract_structure": contract_structure,
        "warnings": warnings,
    }


def add_contract_structure_to_docling_pdf_json_data(
    json_data: dict[str, Any],
    *,
    source_file: str | None = None,
    doc_id: str | None = None,
) -> dict[str, Any]:
    lines = standard_lines_from_docling_json_data(json_data)
    contract_structure, warnings = parse_contract_structure_from_lines(lines)
    enriched = dict(json_data)
    enriched["schema_name"] = (
        json_data.get("schema_name") or DOCLING_PDF_STRUCTURE_SCHEMA_NAME
    )
    enriched["contract_structure"] = contract_structure
    enriched["warnings"] = list(json_data.get("warnings") or []) + warnings
    enriched["contract_structure_parser"] = {
        "name": "contract-structure-parser",
        "source": "docling",
        "doc_id": doc_id,
        "source_file": source_file,
    }
    return enriched


def call_pymupdf4llm_to_markdown(module: Any, pdf_path: Path) -> Any:
    options = {
        "page_chunks": True,
        "header": False,
        "footer": False,
        "page_separators": False,
        "ignore_code": True,
    }
    try:
        return module.to_markdown(str(pdf_path), **options)
    except TypeError:
        fallback_options = {
            "page_chunks": True,
            "page_separators": False,
        }
        return module.to_markdown(str(pdf_path), **fallback_options)


def standard_lines_from_pymupdf4llm_chunks(chunks: Any) -> list[StandardLine]:
    if isinstance(chunks, str):
        return standard_lines_from_markdown(chunks, page_no=None, source="pymupdf4llm")

    if not isinstance(chunks, list):
        return []

    lines: list[StandardLine] = []
    for chunk_index, chunk in enumerate(chunks):
        if isinstance(chunk, str):
            page_no = chunk_index + 1
            lines.extend(
                standard_lines_from_markdown(
                    chunk,
                    page_no=page_no,
                    source="pymupdf4llm",
                    source_ref_prefix=f"#/pages/{chunk_index}/lines",
                )
            )
            continue

        if not isinstance(chunk, dict):
            continue

        page_no = extract_pymupdf4llm_page_no(chunk, chunk_index)
        lines.extend(standard_lines_from_pymupdf4llm_chunk(chunk, chunk_index, page_no))

    return with_page_line_counts(lines)


def standard_lines_from_pymupdf4llm_chunk(
    chunk: dict[str, Any],
    chunk_index: int,
    page_no: int,
) -> list[StandardLine]:
    text = str(chunk.get("text") or "")
    boxes = chunk.get("page_boxes")
    if not isinstance(boxes, list):
        return standard_lines_from_markdown(
            text,
            page_no=page_no,
            source="pymupdf4llm",
            source_ref_prefix=f"#/pages/{chunk_index}/lines",
        )

    lines: list[StandardLine] = []
    for box_position, box in enumerate(boxes):
        if not isinstance(box, dict):
            continue
        box_class = str(box.get("class") or "")
        if box_class in PYMUPDF4LLM_SKIPPED_BOX_CLASSES:
            continue
        start, stop = extract_pymupdf4llm_text_range(box, len(text))
        box_text = text[start:stop]
        box_index = box.get("index")
        if not isinstance(box_index, int):
            box_index = box_position
        lines.extend(
            standard_lines_from_markdown(
                box_text,
                page_no=page_no,
                source="pymupdf4llm",
                source_ref_prefix=f"#/pages/{chunk_index}/boxes/{box_index}/lines",
                bbox=extract_pymupdf4llm_bbox(box),
                default_block_type=pymupdf4llm_box_block_type(box_class),
                extra={
                    "box_index": box_index,
                    "box_class": box_class,
                    "bbox_coord_origin": PYMUPDF4LLM_BBOX_COORD_ORIGIN,
                },
            )
        )

    return lines


def extract_pymupdf4llm_text_range(box: dict[str, Any], text_length: int) -> tuple[int, int]:
    pos = box.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        return (0, text_length)
    try:
        start = max(0, min(text_length, int(pos[0])))
        stop = max(start, min(text_length, int(pos[1])))
    except (TypeError, ValueError):
        return (0, text_length)
    return (start, stop)


def extract_pymupdf4llm_bbox(box: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = box.get("bbox")
    if isinstance(bbox, dict):
        try:
            return (
                float(bbox["l"]),
                float(bbox["t"]),
                float(bbox["r"]),
                float(bbox["b"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    try:
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except (TypeError, ValueError):
        return None


def pymupdf4llm_box_block_type(box_class: str) -> str:
    if box_class == "table":
        return "table"
    if box_class in {"title", "section-header"}:
        return "heading"
    return "text"


def extract_pymupdf4llm_page_no(chunk: dict[str, Any], fallback_index: int) -> int:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    page_no = metadata.get("page_number")
    if isinstance(page_no, int):
        return page_no
    page_no = chunk.get("page")
    if isinstance(page_no, int):
        return page_no + 1
    return fallback_index + 1


def standard_lines_from_markdown(
    markdown: str,
    *,
    page_no: int | None,
    source: str,
    source_ref_prefix: str = "#/lines",
    bbox: tuple[float, float, float, float] | None = None,
    default_block_type: str = "text",
    extra: dict[str, Any] | None = None,
) -> list[StandardLine]:
    raw_lines = [line for line in markdown.splitlines()]
    cleaned_lines = [clean_contract_line(line) for line in raw_lines]
    nonempty_indexes = [index for index, line in enumerate(cleaned_lines) if line]
    line_count = len(nonempty_indexes)
    lines: list[StandardLine] = []

    for output_index, raw_index in enumerate(nonempty_indexes):
        raw = raw_lines[raw_index]
        text = cleaned_lines[raw_index]
        block_type = default_block_type
        if block_type != "table" and is_markdown_table_line(raw):
            block_type = "table"
        if block_type != "table" and raw.strip().startswith("#"):
            block_type = "heading"
        lines.append(
            StandardLine(
                text=text,
                source_ref=f"{source_ref_prefix}/{output_index}",
                page_no=page_no,
                line_index=output_index,
                line_count=line_count,
                block_type=block_type,
                source=source,
                bbox=bbox,
                extra=dict(extra or {}),
            )
        )

    return lines


def standard_lines_from_docling_json_data(json_data: dict[str, Any]) -> list[StandardLine]:
    raw_lines: list[StandardLine] = []
    text_items = merge_docling_inline_text_items(json_data.get("texts") or [])
    for text_index, item in enumerate(text_items):
        if not isinstance(item, dict):
            continue

        text = clean_contract_line(docling_item_text(item))
        if not text:
            continue

        page_no = extract_docling_page_no(item)
        source_ref = item.get("self_ref") or f"#/texts/{text_index}"
        raw_lines.append(
            StandardLine(
                text=text,
                source_ref=source_ref,
                page_no=page_no,
                block_type=docling_block_type(item),
                source="docling",
                extra={"text_index": text_index},
            )
        )

    return with_page_line_counts(raw_lines)


def docling_item_text(item: dict[str, Any]) -> str:
    text = str(item.get("text") or "")
    orig = str(item.get("orig") or "")
    if not orig.strip():
        return text

    orig_token = parse_number_token(orig)
    text_token = parse_number_token(text)
    if orig_token is not None and text_token is None:
        return orig

    if str(item.get("label") or "").lower() == "list_item":
        return orig

    return text


def merge_docling_inline_text_items(items: list[Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = 0
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict):
            index += 1
            continue

        current = dict(item)
        index += 1
        while index < len(items):
            next_item = items[index]
            if not isinstance(next_item, dict) or not should_merge_docling_items(
                current,
                next_item,
            ):
                break
            current = merge_docling_items(current, next_item)
            index += 1
        merged.append(current)
    return merged


def should_merge_docling_items(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if docling_block_type(left) == "table" or docling_block_type(right) == "table":
        return False
    if extract_docling_page_no(left) != extract_docling_page_no(right):
        return False
    if parent_ref(left) != parent_ref(right):
        return False

    left_bbox = extract_docling_bbox(left)
    right_bbox = extract_docling_bbox(right)
    if left_bbox is None or right_bbox is None:
        return False

    left_center = (left_bbox[1] + left_bbox[3]) / 2
    right_center = (right_bbox[1] + right_bbox[3]) / 2
    max_height = max(abs(left_bbox[3] - left_bbox[1]), abs(right_bbox[3] - right_bbox[1]))
    horizontal_gap = right_bbox[0] - left_bbox[2]

    return abs(left_center - right_center) <= max_height * 0.5 and -2 <= horizontal_gap <= 4


def merge_docling_items(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_text = docling_item_text(left)
    right_text = docling_item_text(right)
    left_bbox = extract_docling_bbox(left)
    right_bbox = extract_docling_bbox(right)
    horizontal_gap = right_bbox[0] - left_bbox[2] if left_bbox and right_bbox else 0

    merged = dict(left)
    merged_text = join_inline_text(left_text, right_text, horizontal_gap)
    merged["text"] = merged_text
    if left.get("orig") or right.get("orig"):
        merged["orig"] = merged_text

    if left_bbox and right_bbox and left.get("prov"):
        prov = [dict(left["prov"][0])]
        prov[0]["bbox"] = {
            "l": min(left_bbox[0], right_bbox[0]),
            "t": max(left_bbox[1], right_bbox[1]),
            "r": max(left_bbox[2], right_bbox[2]),
            "b": min(left_bbox[3], right_bbox[3]),
            "coord_origin": "BOTTOMLEFT",
        }
        merged["prov"] = prov
    return merged


def join_inline_text(left: str, right: str, horizontal_gap: float) -> str:
    left = clean_contract_line(left)
    right = clean_contract_line(right)
    if not left:
        return right
    if not right:
        return left
    if horizontal_gap <= 1:
        return left + right
    if is_cjk(left[-1]) or is_cjk(right[0]) or right[0] in "，。；：、,.):）]】":
        return left + right
    return f"{left} {right}"


def is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def parent_ref(item: dict[str, Any]) -> str | None:
    parent = item.get("parent")
    return parent.get("$ref") if isinstance(parent, dict) else None


def extract_docling_bbox(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    prov = item.get("prov") or []
    if not prov or not isinstance(prov[0], dict):
        return None
    bbox = prov[0].get("bbox")
    if not isinstance(bbox, dict):
        return None
    try:
        return (
            float(bbox["l"]),
            float(bbox["t"]),
            float(bbox["r"]),
            float(bbox["b"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def with_page_line_counts(lines: list[StandardLine]) -> list[StandardLine]:
    groups: dict[int | None, list[int]] = defaultdict(list)
    for index, line in enumerate(lines):
        groups[line.page_no].append(index)

    result = list(lines)
    for indexes in groups.values():
        line_count = len(indexes)
        for line_index, original_index in enumerate(indexes):
            line = result[original_index]
            result[original_index] = StandardLine(
                text=line.text,
                source_ref=line.source_ref,
                page_no=line.page_no,
                line_index=line_index,
                line_count=line_count,
                block_type=line.block_type,
                source=line.source,
                bbox=line.bbox,
                extra=line.extra,
            )
    return result


def docling_block_type(item: dict[str, Any]) -> str:
    label = str(item.get("label") or "").lower()
    if "header" in label or "title" in label:
        return "heading"
    if "table" in label:
        return "table"
    return "text"


def extract_docling_page_no(item: dict[str, Any]) -> int | None:
    prov = item.get("prov") or []
    if not prov or not isinstance(prov[0], dict):
        return None
    page_no = prov[0].get("page_no")
    return page_no if isinstance(page_no, int) else None


def build_text_items_from_standard_lines(lines: list[StandardLine]) -> list[dict[str, Any]]:
    text_items = []
    for index, line in enumerate(lines):
        if line.block_type == "table":
            continue
        token = parse_number_token(line.text)
        if token is None:
            token = parse_heading_token(
                line.text,
                is_heading_style=line.block_type == "heading",
            )
        item: dict[str, Any] = {
            "self_ref": f"#/texts/{len(text_items)}",
            "parent": {"$ref": "#/body"},
            "label": "section_header" if token else "text",
            "content_layer": "body",
            "text": line.text,
            "prov": [
                {
                    "page_no": line.page_no,
                    "line_index": line.line_index,
                    "source_ref": line.source_ref,
                }
            ],
            "pdf": {
                "parser": line.source,
                "block_type": line.block_type,
            },
        }
        bbox = standard_line_bbox_payload(line)
        if bbox is not None:
            item["prov"][0]["bbox"] = bbox
        if token is not None:
            item["contract_numbering"] = {
                "kind": token.kind,
                "label": token.raw_label,
                "title": token.title,
                "rank": token.rank,
                "path": list(token.path),
                "source": token.source,
            }
        text_items.append(item)
    return text_items


def build_table_items_from_standard_lines(lines: list[StandardLine]) -> list[dict[str, Any]]:
    tables = []
    for line in lines:
        if line.block_type != "table":
            continue
        item = {
            "self_ref": f"#/tables/{len(tables)}",
            "page_no": line.page_no,
            "line_index": line.line_index,
            "text": line.text,
            "source": line.source,
        }
        bbox = standard_line_bbox_payload(line)
        if bbox is not None:
            item["bbox"] = bbox
        tables.append(item)
    return tables


def standard_line_bbox_payload(line: StandardLine) -> dict[str, Any] | None:
    if line.bbox is None:
        return None
    payload: dict[str, Any] = {
        "l": line.bbox[0],
        "t": line.bbox[1],
        "r": line.bbox[2],
        "b": line.bbox[3],
    }
    coord_origin = line.extra.get("bbox_coord_origin")
    if isinstance(coord_origin, str) and coord_origin:
        payload["coord_origin"] = coord_origin
    return payload
