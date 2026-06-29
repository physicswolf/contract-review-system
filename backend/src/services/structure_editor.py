from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import Settings


DOCUMENT_JSON_FILENAME = "document.json"

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
