from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.config import Settings
from src.services.structure_editor import load_document_json


SHANGHAI_TZ = timezone(timedelta(hours=8))
PARTY_SUFFIX_PATTERN = r"(?:公司|集团|中心|单位|机构|部门)"
TYPE_KEYWORDS = {
    "采购合同": ["采购", "供货", "购买", "购置"],
    "服务合同": ["服务", "咨询", "外包", "运维"],
    "租赁合同": ["租赁", "出租", "承租", "租用"],
    "合作协议": ["合作", "战略", "框架", "联营"],
    "技术合同": ["技术", "开发", "软件", "系统"],
    "保密协议": ["保密", "nda", "机密"],
    "劳动合同": ["劳动", "用工", "聘用", "劳务"],
}
MAX_TITLE_LENGTH = 80
DOCX_TITLE_PARAGRAPH_LIMIT = 30
TITLE_PREFIX_PATTERN = re.compile(r"^(?:合同(?:名称|标题)|项目名称)\s*[：:]\s*")
CLAUSE_PREFIX_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)+|[（(]?\d+[）)]|第[一二三四五六七八九十百千万\d]+[章节条])"
)
TITLE_SUFFIX_PATTERN = re.compile(r"(?:合同|协议)(?:[（(][^）)]{1,20}[）)])?$")


def extract_contract_meta(file_id: str, settings: Settings) -> dict[str, Any]:
    """从 document.json 抽取合同元信息，失败时返回降级默认值。"""
    try:
        document = load_document_json(file_id, settings)
    except Exception:
        return _fallback_meta(file_id)

    origin = document.get("origin") if isinstance(document, dict) else {}
    if not isinstance(origin, dict):
        origin = {}

    filename = str(origin.get("filename") or origin.get("source_file") or file_id)
    contract_name = _extract_title_from_document(document) or _extract_contract_name(
        filename
    )
    structure = document.get("contract_structure")
    party_a, party_b = (
        _extract_parties(structure) if isinstance(structure, dict) else ("", "")
    )
    contract_type = _infer_contract_type(filename)
    now = _now_iso()

    return {
        "file_id": file_id,
        "contract_name": contract_name,
        "party_a": party_a,
        "party_b": party_b,
        "contract_type": contract_type,
        "review_time": now,
        "created_at": now,
        "updated_at": now,
    }


def _extract_contract_name(filename: str) -> str:
    name = normalize_space(Path(filename).stem)
    return name or normalize_space(filename)


def _extract_title_from_document(document: dict[str, Any]) -> str | None:
    texts = document.get("texts")
    if not isinstance(texts, list):
        return None

    candidates: list[tuple[int, int, int, str]] = []
    for text_index, item in enumerate(texts):
        if not isinstance(item, dict):
            continue

        raw_title = normalize_space(str(item.get("text") or ""))
        title = _clean_title_candidate(raw_title)
        if not _is_title_candidate(title):
            continue

        page_no = _item_page_no(item)
        paragraph_index = _item_paragraph_index(item)
        label = normalize_space(str(item.get("label") or "")).lower()
        is_heading = label in {"section_header", "title"}
        priority = _title_priority(page_no, is_heading, paragraph_index, text_index)
        if priority > 0:
            position = paragraph_index if paragraph_index is not None else text_index
            candidates.append((priority, len(title), position, title))

    if not candidates:
        return None

    candidates.sort(key=lambda candidate: (-candidate[0], -candidate[1], candidate[2]))
    return candidates[0][3]


def _clean_title_candidate(value: str) -> str:
    return normalize_space(TITLE_PREFIX_PATTERN.sub("", value))


def _is_title_candidate(title: str) -> bool:
    if not title or "合同" not in title:
        return False
    if len(title) > MAX_TITLE_LENGTH:
        return False
    if CLAUSE_PREFIX_PATTERN.match(title):
        return False
    return TITLE_SUFFIX_PATTERN.search(title) is not None


def _item_page_no(item: dict[str, Any]) -> int | None:
    """从 texts 项中提取页码；DOCX 无页码时返回 None。"""
    prov = item.get("prov")
    if isinstance(prov, list) and prov:
        first = prov[0]
        if isinstance(first, dict):
            page_no = first.get("page_no")
            if isinstance(page_no, int) and page_no > 0:
                return page_no
    return None


def _item_paragraph_index(item: dict[str, Any]) -> int | None:
    prov = item.get("prov")
    if isinstance(prov, list) and prov:
        first = prov[0]
        if isinstance(first, dict):
            paragraph_index = first.get("paragraph_index")
            if isinstance(paragraph_index, int) and paragraph_index >= 0:
                return paragraph_index
    return None


def _title_priority(
    page_no: int | None,
    is_heading: bool,
    paragraph_index: int | None,
    text_index: int,
) -> int:
    if page_no is None:
        if paragraph_index is not None:
            return 8 if paragraph_index <= DOCX_TITLE_PARAGRAPH_LIMIT else 0
        return 8 if text_index <= 5 else 0

    if is_heading:
        if page_no == 1:
            return 10
        if page_no == 2:
            return 7
        return 3
    if page_no == 1:
        return 5
    if page_no == 2:
        return 2
    return 0


def _extract_parties(structure: dict[str, Any]) -> tuple[str, str]:
    texts = _collect_all_text(structure)
    full_text = "\n".join(texts)
    return _extract_party(full_text, "甲方"), _extract_party(full_text, "乙方")


def _extract_party(text: str, label: str) -> str:
    pattern = rf"{label}\s*[：:]\s*([^\n\r；;，,]{{2,50}}?{PARTY_SUFFIX_PATTERN})"
    match = re.search(pattern, text)
    if match is None:
        return ""
    return normalize_space(match.group(1))


def _collect_all_text(root: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    stack: list[dict[str, Any]] = [root]

    while stack:
        node = stack.pop()
        for key in ("title", "raw_text"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value)

        content = node.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    texts.append(item["text"])

        children = node.get("children")
        if isinstance(children, list):
            stack.extend(child for child in reversed(children) if isinstance(child, dict))

    return texts


def _infer_contract_type(filename: str) -> str:
    normalized = normalize_space(filename).lower()
    for contract_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return contract_type
    return "未分类"


def _fallback_meta(file_id: str) -> dict[str, Any]:
    now = _now_iso()
    return {
        "file_id": file_id,
        "contract_name": file_id,
        "party_a": "",
        "party_b": "",
        "contract_type": "未分类",
        "review_time": now,
        "created_at": now,
        "updated_at": now,
    }


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")
