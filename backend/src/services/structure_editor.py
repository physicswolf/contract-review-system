from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.services.contract_structure_parser import (
    StandardLine,
    parse_contract_structure_from_lines,
)


DOCUMENT_JSON_FILENAME = "document.json"
BLOCKS_JSON_FILENAME = "blocks.json"
EDITOR_STRUCTURE_META_KEY = "contract_structure_editor"

ERROR_MESSAGES = {
    "DOCUMENT_NOT_FOUND": "文档不存在或尚未解析完成",
    "STRUCTURE_VALIDATION_ERROR": "文档结构校验失败",
    "INTERNAL_ERROR": "结构保存失败，请稍后重试",
}


class StructureEditorError(Exception):
    def __init__(self, code: str, message: str | None = None, status_code: int = 400):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "文档结构处理失败")
        self.status_code = status_code
        super().__init__(self.message)


class DocumentNotFoundError(StructureEditorError):
    def __init__(self) -> None:
        super().__init__("DOCUMENT_NOT_FOUND", status_code=404)


class StructureValidationError(StructureEditorError):
    def __init__(self, message: str) -> None:
        super().__init__(
            "STRUCTURE_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )


def document_exists(file_id: str, settings: Settings) -> bool:
    """Return whether the parsed document JSON exists."""
    return _document_json_path(file_id, settings).is_file()


def load_document_json(file_id: str, settings: Settings) -> dict[str, Any]:
    """Load the parsed document JSON."""
    path = _document_json_path(file_id, settings)
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(path.read_text(encoding="utf-8"))


def load_blocks_json(file_id: str, settings: Settings) -> dict[str, Any]:
    """Load the parsed blocks JSON."""
    path = _blocks_json_path(file_id, settings)
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(path.read_text(encoding="utf-8"))


def load_editor_structure(
    file_id: str,
    settings: Settings,
    document: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Prefer blocks.json for the editable structure, falling back to document.json."""
    if document is None:
        document = load_document_json(file_id, settings)

    if _has_saved_editor_structure(document):
        return _structure_from_document(document)

    try:
        structure, warnings = build_structure_from_blocks(load_blocks_json(file_id, settings))
        if structure is not None:
            return structure, warnings
    except FileNotFoundError:
        pass

    return _structure_from_document(document)


def _structure_from_document(
    document: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    structure = document.get("contract_structure")
    warnings = document.get("warnings")
    return (
        structure if isinstance(structure, dict) else None,
        warnings if isinstance(warnings, list) else [],
    )


def build_structure_from_blocks(
    blocks_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    raw_blocks = blocks_data.get("blocks")
    if not isinstance(raw_blocks, list):
        return None, []

    lines = []
    for index, block in enumerate(raw_blocks):
        if not isinstance(block, dict):
            continue

        text = str(block.get("text") or "").strip()
        if not text:
            continue

        lines.append(
            StandardLine(
                text=text,
                source_ref=f"#/blocks/{index}",
                page_no=_int_or_none(block.get("page")),
                line_index=_int_or_none(block.get("no")),
                source="blocks",
                bbox=_block_bbox_tuple(block.get("bbox")),
            )
        )

    if not lines:
        return None, []

    return parse_contract_structure_from_lines(lines)


def save_contract_structure(
    file_id: str,
    updated_structure: dict[str, Any],
    settings: Settings,
) -> None:
    """Validate and save contract_structure back to document.json."""
    path = _document_json_path(file_id, settings)
    if not path.is_file():
        raise DocumentNotFoundError()

    _validate_structure_tree(updated_structure)
    document = load_document_json(file_id, settings)
    document["contract_structure"] = updated_structure
    document[EDITOR_STRUCTURE_META_KEY] = {"source": "manual"}
    _write_json_atomically(path, document)


def _validate_structure_tree(node: dict[str, Any]) -> None:
    if not isinstance(node, dict):
        raise StructureValidationError("structure 必须是对象")

    nodes: dict[str, dict[str, Any]] = {}
    parent_ids: dict[str, str | None] = {}
    stack: list[dict[str, Any]] = [node]

    while stack:
        current = stack.pop()
        node_id = current.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise StructureValidationError("每个节点必须包含非空 node_id")

        if node_id in nodes:
            raise StructureValidationError(f"node_id 重复：{node_id}")

        children = current.get("children")
        if not isinstance(children, list):
            raise StructureValidationError(f"节点 {node_id} 的 children 必须是数组")

        nodes[node_id] = current
        parent_id = current.get("parent_id")
        parent_ids[node_id] = parent_id if isinstance(parent_id, str) else None

        for child in children:
            if not isinstance(child, dict):
                raise StructureValidationError(f"节点 {node_id} 的子节点必须是对象")
            stack.append(child)

    if "root" not in nodes:
        raise StructureValidationError("根节点 node_id 必须是 root")

    if parent_ids["root"] is not None:
        raise StructureValidationError("root 节点的 parent_id 必须为空")

    for node_id, parent_id in parent_ids.items():
        if node_id == "root":
            continue
        if parent_id is None or parent_id not in nodes:
            raise StructureValidationError(f"节点 {node_id} 的 parent_id 无效")

    for node_id in nodes:
        seen: set[str] = set()
        current_id: str | None = node_id
        while current_id is not None:
            if current_id in seen:
                raise StructureValidationError(f"节点 {node_id} 存在循环 parent_id 引用")
            seen.add(current_id)
            current_id = parent_ids.get(current_id)


def _write_json_atomically(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".part")
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path.write_text(json_text + "\n", encoding="utf-8")
    temp_path.replace(path)


def _document_json_path(file_id: str, settings: Settings) -> Path:
    return settings.parsing_root / file_id / DOCUMENT_JSON_FILENAME


def _blocks_json_path(file_id: str, settings: Settings) -> Path:
    return settings.parsing_root / file_id / BLOCKS_JSON_FILENAME


def _has_saved_editor_structure(document: dict[str, Any]) -> bool:
    meta = document.get(EDITOR_STRUCTURE_META_KEY)
    return isinstance(meta, dict) and meta.get("source") == "manual"


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _block_bbox_tuple(value: Any) -> tuple[float, float, float, float] | None:
    if isinstance(value, dict):
        if {"x", "y", "width", "height"} <= value.keys():
            x = _float_or_none(value.get("x"))
            y = _float_or_none(value.get("y"))
            width = _float_or_none(value.get("width"))
            height = _float_or_none(value.get("height"))
            if x is not None and y is not None and width is not None and height is not None:
                return (x, y, x + width, y + height)

        if {"l", "t", "r", "b"} <= value.keys():
            left = _float_or_none(value.get("l"))
            top = _float_or_none(value.get("t"))
            right = _float_or_none(value.get("r"))
            bottom = _float_or_none(value.get("b"))
            if left is not None and top is not None and right is not None and bottom is not None:
                return (left, top, right, bottom)

    if isinstance(value, (list, tuple)) and len(value) == 4:
        coords = [_float_or_none(item) for item in value]
        left, top, right, bottom = coords
        if left is not None and top is not None and right is not None and bottom is not None:
            return (left, top, right, bottom)

    return None
