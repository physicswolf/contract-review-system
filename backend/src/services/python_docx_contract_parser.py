from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import docx
from docx import Document
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.services.contract_structure_parser import (
    ClauseNode,
    NumberToken,
    TocContext,
    add_continuity_warning,
    append_node_warnings,
    attach_node,
    format_number,
    normalize_space,
    parse_heading_token,
    parse_number_token,
    serialize_node,
)


SCHEMA_NAME = "PythonDocxContractDocument"
SCHEMA_VERSION = "1.0.0"


class NumberingResolver:
    def __init__(self, doc: Any):
        self.doc = doc
        self.abstract_levels: dict[tuple[int, int], dict[str, Any]] = {}
        self.num_to_abstract: dict[int, int] = {}
        self.start_overrides: dict[tuple[int, int], int] = {}
        self.counters: dict[int, dict[int, int]] = defaultdict(dict)
        self._load_numbering()

    @staticmethod
    def _child_value(parent: Any, tag: str, default: Any = None) -> Any:
        child = parent.find(qn(f"w:{tag}")) if parent is not None else None
        return child.get(qn("w:val")) if child is not None else default

    def _load_numbering(self) -> None:
        try:
            root = self.doc.part.numbering_part.element
        except Exception:
            return

        for abstract in root.findall(qn("w:abstractNum")):
            abstract_id = int(abstract.get(qn("w:abstractNumId")))

            for level in abstract.findall(qn("w:lvl")):
                ilvl = int(level.get(qn("w:ilvl")))
                self.abstract_levels[(abstract_id, ilvl)] = {
                    "start": int(self._child_value(level, "start", "1")),
                    "num_fmt": self._child_value(level, "numFmt", "decimal"),
                    "lvl_text": self._child_value(level, "lvlText", f"%{ilvl + 1}."),
                    "suffix": self._child_value(level, "suff", "tab"),
                    "is_legal": level.find(qn("w:isLgl")) is not None,
                }

        for num in root.findall(qn("w:num")):
            num_id = int(num.get(qn("w:numId")))
            abstract_el = num.find(qn("w:abstractNumId"))
            if abstract_el is None:
                continue

            abstract_id = int(abstract_el.get(qn("w:val")))
            self.num_to_abstract[num_id] = abstract_id

            for override in num.findall(qn("w:lvlOverride")):
                ilvl = int(override.get(qn("w:ilvl")))
                start_override = override.find(qn("w:startOverride"))
                if start_override is not None:
                    self.start_overrides[(num_id, ilvl)] = int(
                        start_override.get(qn("w:val"))
                    )

    @staticmethod
    def _read_numpr(ppr: Any) -> tuple[int | None, int | None]:
        if ppr is None:
            return None, None

        num_pr = ppr.find(qn("w:numPr"))
        if num_pr is None:
            return None, None

        num_id_el = num_pr.find(qn("w:numId"))
        ilvl_el = num_pr.find(qn("w:ilvl"))

        num_id = int(num_id_el.get(qn("w:val"))) if num_id_el is not None else None
        ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else None
        return num_id, ilvl

    def effective_numpr(self, paragraph: Paragraph) -> tuple[int, int] | None:
        direct_num_id, direct_ilvl = self._read_numpr(paragraph._p.pPr)

        if direct_num_id == 0 or direct_ilvl == 255:
            return None

        style_num_id = None
        style_ilvl = None
        style = paragraph.style
        visited = set()

        while style is not None and style.style_id not in visited:
            visited.add(style.style_id)
            num_id, ilvl = self._read_numpr(style.element.pPr)

            if style_num_id is None and num_id is not None:
                style_num_id = num_id
            if style_ilvl is None and ilvl is not None:
                style_ilvl = ilvl

            style = style.base_style

        num_id = direct_num_id if direct_num_id is not None else style_num_id
        ilvl = direct_ilvl if direct_ilvl is not None else style_ilvl

        if num_id in {None, 0}:
            return None

        return num_id, ilvl or 0

    def next_label(self, paragraph: Paragraph) -> dict[str, Any] | None:
        num_pr = self.effective_numpr(paragraph)
        if num_pr is None:
            return None

        num_id, ilvl = num_pr
        abstract_id = self.num_to_abstract.get(num_id)
        if abstract_id is None:
            return None

        spec = self.abstract_levels.get((abstract_id, ilvl))
        if spec is None:
            return None

        state = self.counters[num_id]
        start = self.start_overrides.get((num_id, ilvl), spec["start"])
        state[ilvl] = start if ilvl not in state else state[ilvl] + 1

        for deeper_level in list(state):
            if deeper_level > ilvl:
                del state[deeper_level]

        def replace_placeholder(match: re.Match[str]) -> str:
            referenced_level = int(match.group(1)) - 1
            referenced_spec = self.abstract_levels.get(
                (abstract_id, referenced_level), spec
            )
            value = state.get(referenced_level, referenced_spec["start"])
            num_fmt = "decimal" if spec["is_legal"] else referenced_spec["num_fmt"]
            return format_number(value, num_fmt)

        label = re.sub(r"%([1-9])", replace_placeholder, spec["lvl_text"])

        return {
            "label": label,
            "num_id": num_id,
            "ilvl": ilvl,
            "num_fmt": spec["num_fmt"],
            "lvl_text": spec["lvl_text"],
            "source": "auto",
        }


def parse_docx_contract_to_json_data(docx_path: Path, doc_id: str | None = None) -> dict[str, Any]:
    doc = Document(str(docx_path))
    numbering = NumberingResolver(doc)
    root = ClauseNode(
        node_id="root",
        parent_id=None,
        label="",
        title="ROOT",
        kind="root",
        rank=-1,
    )
    stack = [root]
    texts: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    paragraph_index = -1
    node_index = 0
    toc_context = TocContext()

    blocks = list(iter_block_items(doc))
    for block_index, block in enumerate(blocks):
        if isinstance(block, Paragraph):
            paragraph_index += 1
            text = normalize_space(block.text)
            if not text:
                continue

            outline_level = get_outline_level(block)
            auto = numbering.next_label(block)
            token = parse_number_token(
                text,
                auto_label=auto["label"] if auto else None,
                outline_level=outline_level,
            )
            if token is None:
                token = parse_heading_token(
                    text,
                    is_heading_style=is_heading_paragraph(block),
                    outline_level=outline_level,
                )
            text_item = build_docx_text_item(
                text,
                len(texts),
                paragraph_index,
                block,
                token,
                auto,
            )
            texts.append(text_item)

            if toc_context.should_skip(
                text,
                token,
                paragraph_index=paragraph_index,
            ):
                continue

            if token is not None and is_attachment_list_item(blocks, block_index):
                token = None

            if token is None:
                stack[-1].content.append(
                    {
                        "source_ref": text_item["self_ref"],
                        "paragraph_index": paragraph_index,
                        "text": text,
                    }
                )
                continue

            node_index += 1
            node = attach_node(
                stack,
                token,
                raw_text=text,
                node_id=f"node_{node_index:04d}",
                source_ref=text_item["self_ref"],
            )
            node.paragraph_index = paragraph_index
            node.outline_level = outline_level
            node.auto_label = token.auto_label
            node.literal_label = token.literal_label
            if auto:
                node.num_id = auto["num_id"]
                node.ilvl = auto["ilvl"]
            add_continuity_warning(node)
            append_node_warnings(warnings, node)
        elif isinstance(block, Table):
            table = table_to_payload(block, len(tables))
            tables.append(table)
            stack[-1].tables.append(table)

    return {
        "schema_name": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "name": doc_id or docx_path.stem,
        "origin": {
            "filename": docx_path.name,
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        "parser": {
            "name": "python-docx-contract-parser",
            "python_docx": getattr(docx, "__version__", None),
        },
        "texts": texts,
        "tables": tables,
        "contract_structure": serialize_node(root),
        "warnings": warnings,
    }


def build_docx_text_item(
    text: str,
    text_index: int,
    paragraph_index: int,
    paragraph: Paragraph,
    token: NumberToken | None,
    auto: dict[str, Any] | None,
) -> dict[str, Any]:
    label = "section_header" if token is not None else "text"
    item: dict[str, Any] = {
        "self_ref": f"#/texts/{text_index}",
        "parent": {"$ref": "#/body"},
        "label": label,
        "content_layer": "body",
        "text": text,
        "prov": [{"paragraph_index": paragraph_index}],
        "docx": {
            "style": paragraph.style.name if paragraph.style is not None else None,
            "outline_level": get_outline_level(paragraph),
            "auto_label": auto["label"] if auto else None,
        },
    }
    if token is not None:
        item["contract_numbering"] = {
            "kind": token.kind,
            "label": token.raw_label,
            "title": token.title,
            "rank": token.rank,
            "path": list(token.path),
            "source": token.source,
        }
    return item


def iter_block_items(parent: Any):
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def is_attachment_list_item(blocks: list[Any], block_index: int) -> bool:
    current = attachment_list_token_for_block(blocks[block_index])
    if current is None:
        return False

    previous_item = (
        attachment_list_token_for_block(blocks[block_index - 1])
        if block_index > 0
        else None
    )
    next_item = (
        attachment_list_token_for_block(blocks[block_index + 1])
        if block_index + 1 < len(blocks)
        else None
    )
    return previous_item is not None or next_item is not None


def attachment_list_token_for_block(block: Any) -> NumberToken | None:
    if not isinstance(block, Paragraph):
        return None

    token = parse_number_token(normalize_space(block.text))
    if token is None or token.kind != "attachment" or not token.title:
        return None
    return token


def table_to_payload(table: Table, table_index: int) -> dict[str, Any]:
    rows = []
    for row in table.rows:
        rows.append([normalize_space(cell.text) for cell in row.cells])

    column_count = max((len(row) for row in rows), default=0)
    return {
        "self_ref": f"#/tables/{table_index}",
        "row_count": len(rows),
        "column_count": column_count,
        "rows": rows,
    }


def get_outline_level(paragraph: Paragraph) -> int | None:
    ppr = paragraph._p.pPr
    if ppr is None:
        return None

    outline = ppr.find(qn("w:outlineLvl"))
    if outline is None:
        return None

    return int(outline.get(qn("w:val")))


def is_heading_paragraph(paragraph: Paragraph) -> bool:
    style = paragraph.style
    if style is None:
        return False

    style_name = str(style.name or "").lower()
    style_id = str(style.style_id or "").lower()
    return (
        style_name.startswith("heading")
        or style_name.startswith("标题")
        or style_id.startswith("heading")
    )
