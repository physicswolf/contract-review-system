from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docx import Document
from docx.text.paragraph import Paragraph

from src.config import Settings
from src.services.contract_structure_parser import normalize_space, parse_number_token
from src.services.python_docx_contract_parser import NumberingResolver, iter_block_items
from src.services.structure_editor import load_document_json


BLOCKS_JSON_FILENAME = "blocks.json"
PRIMARY_STOPS = ":：,，。"
FALLBACK_STOPS = ":：,，。;；"


@dataclass
class MarkdownLine:
    no: int
    text: str
    token: Any | None
    title_page: bool = False
    start: int | None = None
    end: int | None = None


@dataclass
class DocumentUnit:
    order: int
    page: int
    line_index: int
    text: str
    bbox: dict[str, float]
    start: int = 0
    end: int = 0


def build_blocks_json(
    file_id: str,
    source_path: Path,
    extension: str,
    settings: Settings,
) -> dict[str, Any]:
    document = load_document_json(file_id, settings)
    if extension.lower() == ".docx":
        return _build_docx_blocks(source_path, document)
    return _build_pdf_blocks(document)


def _build_docx_blocks(source_path: Path, document: dict[str, Any]) -> dict[str, Any]:
    md_lines = _parse_markdown_lines(_extract_markdown_lines(source_path))
    total_pages, units = _load_document_units(document)
    flat_text = _build_flat_document(units)
    _locate_markdown_lines(md_lines, flat_text, units)

    blocks = []
    for line in md_lines:
        page, bbox = _build_bbox(_units_for_range(units, line.start, line.end))
        blocks.append(
            {
                "no": line.no,
                "page": page,
                "text": line.text,
                "bbox": bbox,
            }
        )

    return {"total_pages": total_pages, "blocks": blocks}


def _build_pdf_blocks(document: dict[str, Any]) -> dict[str, Any]:
    total_pages, units = _load_document_units(document)
    blocks = []
    for no, unit in enumerate(units, 1):
        blocks.append(
            {
                "no": no,
                "page": unit.page,
                "text": unit.text,
                "bbox": _bbox_to_block_bbox(unit.bbox),
            }
        )
    return {"total_pages": total_pages, "blocks": blocks}


def _extract_markdown_lines(docx_path: Path) -> list[str]:
    document = Document(str(docx_path))
    numbering = NumberingResolver(document)
    lines: list[str] = []

    for block in iter_block_items(document):
        if not isinstance(block, Paragraph):
            continue
        text = normalize_space(block.text)
        if not text:
            continue

        auto = numbering.next_label(block)
        label = str(auto.get("label") or "") if auto else ""
        lines.append(_prepend_label(label, text))

    return lines


def _prepend_label(label: str, text: str) -> str:
    if not label:
        return text
    if normalize_match(text).startswith(normalize_match(label)):
        return text
    return f"{label}{text}"


def _parse_markdown_lines(raw_lines: list[str]) -> list[MarkdownLine]:
    lines = [
        MarkdownLine(no=index + 1, text=text, token=parse_number_token(text))
        for index, text in enumerate(raw_lines)
        if text.strip()
    ]
    first_top_level = next(
        (index for index, line in enumerate(lines) if line.token and line.token.rank == 0),
        None,
    )
    if first_top_level is not None:
        for line in lines[:first_top_level]:
            line.title_page = True
    return lines


def _load_document_units(document: dict[str, Any]) -> tuple[int, list[DocumentUnit]]:
    toc_pages = _find_toc_pages(document)
    units: list[DocumentUnit] = []
    total_pages = 0
    order = 0

    for collection in ("texts", "tables"):
        items = document.get(collection)
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            page, line_index, bbox = _extract_bbox(item)
            text = _clean_document_text(str(item.get("text") or ""))
            if page is None or bbox is None or not text:
                continue

            page = int(page)
            total_pages = max(total_pages, page)
            if page in toc_pages or ".........." in text:
                continue

            units.append(
                DocumentUnit(
                    order=order,
                    page=page,
                    line_index=int(line_index or 0),
                    text=text,
                    bbox=bbox,
                )
            )
            order += 1

    units.sort(key=lambda unit: (unit.page, unit.line_index, unit.order))
    return max(total_pages, 1), units


def _find_toc_pages(document: dict[str, Any]) -> set[int]:
    pages: set[int] = set()
    texts = document.get("texts")
    if not isinstance(texts, list):
        return pages

    for item in texts:
        if not isinstance(item, dict) or str(item.get("text") or "").strip() != "目录":
            continue
        page, _, _ = _extract_bbox(item)
        if page is not None:
            pages.add(int(page))
    return pages


def _extract_bbox(
    item: dict[str, Any],
) -> tuple[int | None, int | None, dict[str, float] | None]:
    if isinstance(item.get("bbox"), dict):
        return _page_no(item), _line_index(item), _normalize_bbox(item["bbox"])

    prov = item.get("prov")
    if isinstance(prov, list) and prov and isinstance(prov[0], dict):
        first = prov[0]
        bbox = first.get("bbox")
        if isinstance(bbox, dict):
            return _page_no(first), _line_index(first), _normalize_bbox(bbox)

    return None, None, None


def _page_no(item: dict[str, Any]) -> int | None:
    value = item.get("page_no", item.get("page"))
    return int(value) if isinstance(value, int) else None


def _line_index(item: dict[str, Any]) -> int | None:
    value = item.get("line_index")
    return int(value) if isinstance(value, int) else None


def _normalize_bbox(raw_bbox: dict[str, Any]) -> dict[str, float] | None:
    try:
        return {key: float(raw_bbox[key]) for key in ("l", "t", "r", "b")}
    except (KeyError, TypeError, ValueError):
        return None


def _build_flat_document(units: list[DocumentUnit]) -> str:
    chunks: list[str] = []
    position = 0
    for unit in units:
        normalized = normalize_match(unit.text)
        unit.start = position
        unit.end = position + len(normalized)
        chunks.append(normalized)
        chunks.append("\n")
        position = unit.end + 1
    return "".join(chunks)


def _locate_markdown_lines(
    lines: list[MarkdownLine],
    flat_text: str,
    units: list[DocumentUnit],
) -> None:
    cursor = 0
    for index, line in enumerate(lines):
        found, next_cursor = _find_line_start(line, flat_text, units, cursor)
        next_found = None
        if index + 1 < len(lines):
            next_found, _ = _find_line_start(lines[index + 1], flat_text, units, cursor)
        if found is not None and next_found is not None and found > next_found:
            found = None

        line.start = found
        if found is not None:
            cursor = next_cursor

    matched_starts = [line.start for line in lines if line.start is not None]
    for index, line in enumerate(lines):
        if line.start is None:
            continue

        boundary = None
        if line.token is not None and not line.title_page:
            for next_line in lines[index + 1 :]:
                if (
                    next_line.start is not None
                    and next_line.token is not None
                    and not next_line.title_page
                    and next_line.token.rank <= line.token.rank
                ):
                    boundary = next_line.start
                    break
        else:
            boundary = next((start for start in matched_starts if start > line.start), None)

        line.end = boundary if boundary is not None else len(flat_text)


def _find_line_start(
    line: MarkdownLine,
    flat_text: str,
    units: list[DocumentUnit],
    cursor: int,
) -> tuple[int | None, int]:
    candidates = _match_candidates(line.text)
    for candidate in candidates:
        normalized = normalize_match(candidate)
        found = flat_text.find(normalized, cursor)
        if found >= 0:
            return found, found + max(1, len(normalized))

    for candidate in candidates:
        for shortened in _shortened_candidates(candidate):
            found = flat_text.find(shortened, cursor)
            if found >= 0:
                return found, found + max(1, len(shortened))

    loose_cursor_unit = next((index for index, unit in enumerate(units) if unit.end >= cursor), 0)
    for candidate in candidates:
        normalized = _loose_match(candidate)
        if not normalized:
            continue
        for unit in units[loose_cursor_unit:]:
            if normalized in _loose_match(unit.text):
                return unit.start, unit.start + 1
    return None, cursor


def _match_candidates(text: str) -> list[str]:
    candidates = []
    for stops in (PRIMARY_STOPS, FALLBACK_STOPS):
        match = re.search(f"[{re.escape(stops)}]", text)
        candidate = text[: match.start()] if match else text
        candidate = candidate.strip()
        if candidate:
            candidates.append(candidate)
    candidates.append(text)

    unique = []
    seen = set()
    for candidate in candidates:
        normalized = normalize_match(candidate)
        if normalized and normalized not in seen:
            unique.append(candidate)
            seen.add(normalized)
    return unique


def _shortened_candidates(candidate: str, min_length: int = 5):
    normalized = normalize_match(candidate)
    for length in range(len(normalized) - 1, min_length - 1, -1):
        yield normalized[:length]


def _units_for_range(
    units: list[DocumentUnit],
    start: int | None,
    end: int | None,
) -> list[DocumentUnit]:
    if start is None or end is None:
        return []
    return [unit for unit in units if unit.start < end and unit.end > start]


def _build_bbox(units: list[DocumentUnit]) -> tuple[int | None, dict[str, float]]:
    valid = [unit for unit in units if {"l", "t", "r", "b"} <= unit.bbox.keys()]
    if not valid:
        return None, {}

    page = valid[0].page
    same_page_units = [unit for unit in valid if unit.page == page]
    return page, _union_block_bbox([unit.bbox for unit in same_page_units])


def _union_block_bbox(bboxes: list[dict[str, float]]) -> dict[str, float]:
    left = min(min(bbox["l"], bbox["r"]) for bbox in bboxes)
    right = max(max(bbox["l"], bbox["r"]) for bbox in bboxes)
    top = min(min(bbox["t"], bbox["b"]) for bbox in bboxes)
    bottom = max(max(bbox["t"], bbox["b"]) for bbox in bboxes)
    return {
        "x": _round_number(left),
        "y": _round_number(top),
        "width": _round_number(max(0.0, right - left)),
        "height": _round_number(max(0.0, bottom - top)),
    }


def _bbox_to_block_bbox(bbox: dict[str, float]) -> dict[str, float]:
    return _union_block_bbox([bbox])


def _round_number(value: float) -> int | float:
    if value == int(value):
        return int(value)
    return round(value, 3)


def _clean_document_text(text: str) -> str:
    text = text.replace("<br>", "")
    return re.sub(r"^\s*-\s+", "", text)


def normalize_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("：", ":")
        .replace("，", ",")
        .replace("；", ";")
        .replace("。", ".")
    )
    return re.sub(r"\s+", "", text)


def _loose_match(text: str) -> str:
    text = normalize_match(text).lower()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
