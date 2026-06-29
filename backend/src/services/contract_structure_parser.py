from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


CN = "零〇一二三四五六七八九十百千万两"
HEADING_RANK = 15
TOC_MARKERS = {"目 录", "目录"}
TOC_PARAGRAPH_GAP = 3
PLAIN_HEADING_TITLES = {
    "定义",
    "前言",
    "总则",
    "双方权利义务",
    "合同首部",
}
HEADING_END_PUNCTUATION = ("。", "；", "：", ":", "！", "？", "，", ",", "、", ";")


@dataclass
class NumberToken:
    kind: str
    raw_label: str
    title: str
    rank: int
    path: tuple[int, ...] = ()
    source: str = "literal"
    auto_label: str | None = None
    literal_label: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ClauseNode:
    node_id: str
    parent_id: str | None
    label: str
    title: str
    kind: str
    rank: int
    path: tuple[int, ...] = ()
    source: str = "literal"
    raw_text: str = ""
    source_ref: str | None = None
    auto_label: str | None = None
    literal_label: str | None = None
    num_id: int | None = None
    ilvl: int | None = None
    outline_level: int | None = None
    paragraph_index: int | None = None
    page_no: int | None = None
    line_index: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    content: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    children: list["ClauseNode"] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StandardLine:
    text: str
    source_ref: str
    page_no: int | None = None
    line_index: int | None = None
    line_count: int | None = None
    block_type: str = "text"
    source: str = "text"
    bbox: tuple[float, float, float, float] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def parse_number_token(
    text: str,
    auto_label: str | None = None,
    outline_level: int | None = None,
) -> NumberToken | None:
    original_text = normalize_space(text)

    if auto_label:
        literal_token = parse_number_token(original_text, outline_level=outline_level)
        auto_token = parse_number_token(
            f"{auto_label}{original_text}",
            outline_level=outline_level,
        )
        if literal_token is not None:
            literal_token.auto_label = auto_label
            literal_token.literal_label = literal_token.raw_label
            literal_token.warnings.append("自动编号与文本编号同时存在")
            return literal_token
        if auto_token is not None:
            auto_token.title = original_text
            auto_token.source = "auto"
            auto_token.auto_label = auto_label
        return auto_token

    normalized = clean_contract_line(original_text)
    normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", normalized)

    match = re.match(rf"^(第[{CN}0-9]+部分)\s*(.*)$", normalized)
    if match:
        return NumberToken("part", match.group(1), match.group(2).strip(), 0)

    match = re.match(rf"^(第[{CN}0-9]+章)\s*[:：]?\s*(.*)$", normalized)
    if match:
        return NumberToken("chapter", match.group(1), match.group(2).strip(), 0)

    match = re.match(rf"^(附件[{CN}0-9]+)\s*[:：]?\s*(.*)$", normalized)
    if match:
        return NumberToken("attachment", match.group(1), match.group(2).strip(), 5)

    match = re.match(rf"^(第[{CN}0-9]+条)\s*(.*)$", normalized)
    if match:
        return NumberToken("article", match.group(1), match.group(2).strip(), 10)

    match = re.match(rf"^([{CN}]+)、\s*(.*)$", normalized)
    if match:
        return NumberToken("chinese", match.group(1) + "、", match.group(2).strip(), 10)

    match = re.match(r"^(\d+(?:\.\d+)+)\.?\s*(.*)$", normalized)
    if match:
        path = tuple(int(value) for value in match.group(1).split("."))
        if is_likely_date_path(path):
            return None
        internal_dot_count = len(path) - 1
        return NumberToken(
            "dotted",
            match.group(1),
            match.group(2).strip(),
            20 + internal_dot_count,
            path,
        )

    match = re.match(r"^(\d+)([、.])\s*(?!\d)(.*)$", normalized)
    if match:
        value = int(match.group(1))
        if value > 999:
            return None
        return NumberToken(
            "arabic",
            match.group(1) + match.group(2),
            match.group(3).strip(),
            20,
            (value,),
        )

    match = re.match(rf"^([（(]\s*([{CN}0-9]+)\s*[）)])\s*(.*)$", normalized)
    if match:
        inner = match.group(2)
        path = (int(inner),) if inner.isdigit() else ()
        return NumberToken(
            "parenthesized",
            match.group(1),
            match.group(3).strip(),
            40,
            path,
        )

    return None


def parse_heading_token(
    text: str,
    *,
    is_heading_style: bool = False,
    outline_level: int | None = None,
) -> NumberToken | None:
    title = clean_contract_line(text)
    if not is_standalone_heading_title(
        title,
        is_heading_style=is_heading_style,
        outline_level=outline_level,
    ):
        return None

    return NumberToken(
        "heading",
        "",
        title,
        HEADING_RANK,
        source="heading",
    )


def is_standalone_heading_title(
    title: str,
    *,
    is_heading_style: bool = False,
    outline_level: int | None = None,
) -> bool:
    if not title or len(title) > 20:
        return False
    if title.endswith(HEADING_END_PUNCTUATION):
        return False
    if re.search(r"[。；;：:]", title):
        return False
    if is_heading_style or outline_level is not None:
        return True
    return title in PLAIN_HEADING_TITLES


def parse_contract_structure_from_lines(
    lines: list[StandardLine],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = ClauseNode(
        node_id="root",
        parent_id=None,
        label="",
        title="ROOT",
        kind="root",
        rank=-1,
    )
    stack = [root]
    warnings: list[dict[str, Any]] = []
    node_index = 0
    started = False
    toc_context = TocContext()

    for line_position, line in enumerate(lines):
        text = clean_contract_line(line.text)
        if not text:
            continue

        if should_skip_heading_parse(line):
            if started and is_table_line(line):
                stack[-1].tables.append(line_to_table_payload(line))
            continue

        if is_page_number_line(text, line.line_index, line.line_count):
            continue

        outline_level = line.extra.get("outline_level")
        if not isinstance(outline_level, int):
            outline_level = None
        token = parse_number_token(text, outline_level=outline_level)
        if token is None:
            token = parse_heading_token(
                text,
                is_heading_style=line.block_type == "heading",
                outline_level=outline_level,
            )

        paragraph_index = line.extra.get("paragraph_index")
        if not isinstance(paragraph_index, int):
            paragraph_index = None
        if toc_context.should_skip(
            text,
            token,
            paragraph_index=paragraph_index,
            page_no=line.page_no,
            line_index=line.line_index,
        ):
            continue

        if (
            token is not None
            and token.kind == "chapter"
            and line.source == "docling"
            and line.block_type != "heading"
        ):
            token = None
        if token is not None and is_attachment_list_line(lines, line, line_position):
            token = None

        if not started:
            if token is not None and token.kind in {
                "part",
                "chapter",
                "attachment",
                "heading",
            }:
                started = True
            else:
                append_content(stack[-1], line, text)
                continue

        if token is None:
            append_content(stack[-1], line, text)
            continue

        node_index += 1
        node = attach_node(
            stack,
            token,
            raw_text=text,
            node_id=f"node_{node_index:04d}",
            source_ref=line.source_ref,
        )
        node.page_no = line.page_no
        node.line_index = line.line_index
        node.bbox = line.bbox
        add_continuity_warning(node)
        append_node_warnings(warnings, node)

    return serialize_node(root), warnings


class TocContext:
    def __init__(self) -> None:
        self.active = False
        self.previous_paragraph_index: int | None = None
        self.previous_page_no: int | None = None

    def should_skip(
        self,
        text: str,
        token: NumberToken | None,
        *,
        paragraph_index: int | None = None,
        page_no: int | None = None,
        line_index: int | None = None,
    ) -> bool:
        if is_toc_marker(text):
            self._activate(paragraph_index, page_no)
            return True

        if has_toc_page_reference(text):
            self._remember(paragraph_index, page_no)
            return True

        if not self.active:
            return False

        if self._should_end_before_line(paragraph_index, page_no, line_index):
            self.active = False
            return False

        if is_toc_entry(text, token):
            self._remember(paragraph_index, page_no)
            return True

        self.active = False
        return False

    def _activate(
        self,
        paragraph_index: int | None,
        page_no: int | None,
    ) -> None:
        self.active = True
        self._remember(paragraph_index, page_no)

    def _remember(
        self,
        paragraph_index: int | None,
        page_no: int | None,
    ) -> None:
        if paragraph_index is not None:
            self.previous_paragraph_index = paragraph_index
        if page_no is not None:
            self.previous_page_no = page_no

    def _should_end_before_line(
        self,
        paragraph_index: int | None,
        page_no: int | None,
        line_index: int | None,
    ) -> bool:
        if (
            paragraph_index is not None
            and self.previous_paragraph_index is not None
            and paragraph_index - self.previous_paragraph_index > TOC_PARAGRAPH_GAP
        ):
            return True

        return (
            page_no is not None
            and self.previous_page_no is not None
            and page_no != self.previous_page_no
            and (line_index is None or line_index <= 1)
        )


def attach_node(
    stack: list[ClauseNode],
    token: NumberToken,
    *,
    raw_text: str,
    node_id: str,
    source_ref: str,
) -> ClauseNode:
    while len(stack) > 1 and stack[-1].rank >= token.rank:
        stack.pop()

    parent = stack[-1]
    missing_dotted_parent = False

    if token.kind == "dotted" and token.path:
        expected_parent_path = token.path[:-1]
        found_parent_by_path = False

        for ancestor in reversed(stack):
            if expected_parent_path and ancestor.path == expected_parent_path:
                parent = ancestor
                found_parent_by_path = True
                break

            if ancestor.kind in {"part", "chapter", "attachment", "chinese", "article"}:
                break

        missing_dotted_parent = bool(expected_parent_path and not found_parent_by_path)

    if parent.children:
        last = parent.children[-1]
        if last.label == token.raw_label and last.title == token.title:
            last.warnings.append("疑似分页重复标题，已合并")
            return last

    node = ClauseNode(
        node_id=node_id,
        parent_id=parent.node_id,
        label=token.raw_label,
        title=token.title,
        kind=token.kind,
        rank=token.rank,
        path=token.path,
        source=token.source,
        raw_text=raw_text,
        source_ref=source_ref,
        auto_label=token.auto_label,
        literal_label=token.literal_label,
        warnings=list(token.warnings),
    )
    if missing_dotted_parent:
        node.warnings.append("dotted 编号缺少显式父节点")

    parent.children.append(node)
    setattr(node, "_parent_children", parent.children)
    stack.append(node)
    return node


def append_content(node: ClauseNode, line: StandardLine, text: str) -> None:
    content = {
        "source_ref": line.source_ref,
        "page_no": line.page_no,
        "line_index": line.line_index,
        "text": text,
    }

    if node.kind == "attachment" and not node.title:
        node.title = text
        return

    if node.content:
        previous = node.content[-1]
        previous_text = previous.get("text", "")
        if previous_text and not previous_text.endswith(("。", "；", "：", ":", "！", "？")):
            previous["text"] = previous_text + text
            return

    node.content.append(content)


def add_continuity_warning(node: ClauseNode) -> None:
    if node.parent_id is None or not node.path:
        return

    siblings = getattr(node, "_parent_children", [])
    previous = None
    for sibling in reversed(siblings[:-1]):
        if sibling.kind == node.kind and len(sibling.path) == len(node.path):
            previous = sibling
            break

    if previous is None or not previous.path:
        return

    same_parent_path = previous.path[:-1] == node.path[:-1]
    if same_parent_path and previous.path[-1] + 1 != node.path[-1]:
        node.warnings.append(
            f"同级编号不连续：{format_path(previous.path)} 后出现 {format_path(node.path)}"
        )


def append_node_warnings(warnings: list[dict[str, Any]], node: ClauseNode) -> None:
    for message in node.warnings:
        warnings.append(
            {
                "node_id": node.node_id,
                "source_ref": node.source_ref,
                "message": message,
            }
        )


def serialize_node(node: ClauseNode, depth: int = 0) -> dict[str, Any]:
    children = [serialize_node(child, depth + 1) for child in node.children]
    children = remove_empty_duplicate_nodes(children)
    content = node.content
    tables = node.tables

    if node.kind == "root" and (node.content or node.tables):
        children.insert(0, preamble_node_payload(node, depth + 1))
        content = []
        tables = []

    return {
        "node_id": node.node_id,
        "parent_id": node.parent_id,
        "label": node.label,
        "title": node.title,
        "kind": node.kind,
        "rank": node.rank,
        "path": list(node.path),
        "source": node.source,
        "raw_text": node.raw_text,
        "source_ref": node.source_ref,
        "auto_label": node.auto_label,
        "literal_label": node.literal_label,
        "num_id": node.num_id,
        "ilvl": node.ilvl,
        "outline_level": node.outline_level,
        "paragraph_index": node.paragraph_index,
        "page_no": node.page_no,
        "line_index": node.line_index,
        "bbox": list(node.bbox) if node.bbox else None,
        "tree_depth": depth,
        "content": content,
        "tables": tables,
        "warnings": node.warnings,
        "children": children,
    }


def preamble_node_payload(node: ClauseNode, depth: int) -> dict[str, Any]:
    return {
        "node_id": "node_preamble",
        "parent_id": node.node_id,
        "label": "",
        "title": "合同首部",
        "kind": "preamble",
        "rank": -1,
        "path": [],
        "source": "virtual",
        "raw_text": "",
        "source_ref": None,
        "auto_label": None,
        "literal_label": None,
        "num_id": None,
        "ilvl": None,
        "outline_level": None,
        "paragraph_index": None,
        "page_no": None,
        "line_index": None,
        "bbox": None,
        "tree_depth": depth,
        "content": node.content,
        "tables": node.tables,
        "warnings": [],
        "children": [],
    }


def remove_empty_duplicate_nodes(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_non_empty: set[tuple[str, str, str]] = set()
    result: list[dict[str, Any]] = []

    for child in reversed(children):
        key = duplicate_node_key(child)
        if is_empty_structure_node(child) and key in seen_non_empty:
            continue
        if not is_empty_structure_node(child):
            seen_non_empty.add(key)
        result.append(child)

    return list(reversed(result))


def duplicate_node_key(node: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(node.get("kind") or ""),
        str(node.get("label") or ""),
        str(node.get("title") or ""),
    )


def is_empty_structure_node(node: dict[str, Any]) -> bool:
    return not node.get("content") and not node.get("tables") and not node.get("children")


def should_skip_heading_parse(line: StandardLine) -> bool:
    if line.block_type in {"table", "picture", "page_header", "page_footer"}:
        return True
    return is_markdown_table_line(line.text)


def is_table_line(line: StandardLine) -> bool:
    return line.block_type == "table" or is_markdown_table_line(line.text)


def line_to_table_payload(line: StandardLine) -> dict[str, Any]:
    return {
        "source_ref": line.source_ref,
        "page_no": line.page_no,
        "line_index": line.line_index,
        "text": line.text,
        "source": line.source,
    }


def is_attachment_list_line(
    lines: list[StandardLine],
    line: StandardLine,
    line_position: int,
) -> bool:
    if not attachment_list_token_for_line(line):
        return False

    previous_item = (
        attachment_list_token_for_line(lines[line_position - 1])
        if line_position > 0
        else None
    )
    next_item = (
        attachment_list_token_for_line(lines[line_position + 1])
        if line_position + 1 < len(lines)
        else None
    )
    return previous_item is not None or next_item is not None


def attachment_list_token_for_line(line: StandardLine) -> NumberToken | None:
    token = parse_number_token(line.text)
    if token is None or token.kind != "attachment" or not token.title:
        return None
    return token


def is_page_number_line(
    line: str,
    line_index: int | None,
    line_count: int | None,
) -> bool:
    text = line.strip()
    if not re.fullmatch(r"\d{1,3}", text):
        return False
    if line_index is None or line_count is None:
        return True
    return line_index <= 1 or line_index >= line_count - 2


def is_toc_line(line: str) -> bool:
    text = line.strip()
    return is_toc_marker(text) or has_toc_page_reference(text)


def is_toc_marker(line: str) -> bool:
    return line.strip() in TOC_MARKERS


def has_toc_page_reference(line: str) -> bool:
    text = line.strip()
    return bool(re.search(r"[.·…]{3,}\s*\d+$", text))


def is_toc_entry(line: str, token: NumberToken | None) -> bool:
    text = line.strip()
    if has_toc_page_reference(text):
        return True
    if token is not None and token.kind in {"part", "chapter", "attachment", "heading"}:
        return True
    if text in PLAIN_HEADING_TITLES:
        return True
    return bool(re.match(r"^(?:附件|附录|附加)[一二三四五六七八九十百千万\d]?", text))


def is_markdown_table_line(line: str) -> bool:
    text = line.strip()
    return text.startswith("|") and text.endswith("|")


def clean_contract_line(line: Any) -> str:
    text = unicodedata.normalize("NFKC", str(line or ""))
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", text)
    return normalize_space(text)


def chinese_number(n: int) -> str:
    digits = "零一二三四五六七八九"

    if 0 <= n <= 10:
        return "十" if n == 10 else digits[n]
    if n < 20:
        return "十" + digits[n % 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")

    return str(n)


def format_number(value: int, num_fmt: str) -> str:
    if num_fmt in {"chineseCounting", "chineseCountingThousand"}:
        return chinese_number(value)
    return str(value)


def is_likely_date_path(path: tuple[int, ...]) -> bool:
    return bool(path and path[0] >= 1900)


def format_path(path: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in path)


def normalize_space(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()
