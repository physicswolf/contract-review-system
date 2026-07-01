from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any

import httpx

from src.config import Settings, get_settings
from src.services.contract_type_store import contract_type_repository
from src.services.structure_editor import load_document_json


logger = logging.getLogger(__name__)
MAX_PREAMBLE_LINES = 30
MAX_PREAMBLE_CHARS = 4000
SYSTEM_PROMPT = "你是合同类型识别助手。根据合同首部内容判断合同类型，只能从给定清单中选择一项。"


def classify_contract_type(file_id: str) -> tuple[str, int] | None:
    """Use the configured LLM to infer a contract type, or return None for fallback."""
    settings = get_settings()
    _write_llm_log(
        settings,
        "classification.start",
        {
            "file_id": file_id,
            "llm_api_url": str(settings.llm_api_url),
            "llm_model_name": settings.llm_model_name,
            "timeout": settings.llm_classify_timeout,
        },
    )
    if not str(settings.llm_api_url or "").strip():
        _write_llm_log(settings, "classification.skip", {"file_id": file_id, "reason": "llm_api_url_blank"})
        return None

    preamble = _extract_preamble(file_id, settings)
    if not preamble:
        _write_llm_log(settings, "classification.skip", {"file_id": file_id, "reason": "preamble_empty"})
        return None
    _write_llm_log(
        settings,
        "preamble.extracted",
        {
            "file_id": file_id,
            "line_count": len(preamble.splitlines()),
            "char_count": len(preamble),
            "text": preamble,
        },
    )

    type_names = _enabled_type_names()
    _write_llm_log(
        settings,
        "contract_types.loaded",
        {"file_id": file_id, "count": len(type_names), "names": type_names},
    )
    if len(type_names) < 2:
        _write_llm_log(settings, "classification.skip", {"file_id": file_id, "reason": "type_count_less_than_2"})
        return None

    prompt = _build_prompt(preamble, type_names)
    _write_llm_log(
        settings,
        "prompt.built",
        {
            "file_id": file_id,
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt": prompt,
        },
    )
    raw_result = _call_llm(prompt, settings)
    if raw_result is None:
        _write_llm_log(settings, "classification.fallback", {"file_id": file_id, "reason": "llm_result_none"})
        return None

    result = raw_result.strip().strip("\"'“”‘’")
    for name in type_names:
        if name in result:
            confidence = _confidence_from_response(result, name)
            _write_llm_log(
                settings,
                "classification.matched",
                {
                    "file_id": file_id,
                    "raw_result": raw_result,
                    "normalized_result": result,
                    "matched_type": name,
                    "confidence": confidence,
                },
            )
            return name, confidence
    _write_llm_log(
        settings,
        "classification.fallback",
        {
            "file_id": file_id,
            "reason": "result_not_in_type_names",
            "raw_result": raw_result,
            "normalized_result": result,
            "type_names": type_names,
        },
    )
    return None


def _extract_preamble(file_id: str, settings: Settings) -> str:
    try:
        document = load_document_json(file_id, settings)
    except Exception:
        return ""

    structure = document.get("contract_structure") if isinstance(document, dict) else None
    if not isinstance(structure, dict):
        return ""

    texts: list[str] = []
    for child in structure.get("children") or []:
        if isinstance(child, dict) and child.get("kind") == "preamble":
            texts.extend(_content_texts(child))
            break

    if not texts:
        texts.extend(_content_texts(structure))

    return "\n".join(texts[:MAX_PREAMBLE_LINES])[:MAX_PREAMBLE_CHARS].strip()


def _enabled_type_names() -> list[str]:
    try:
        records = contract_type_repository.find_all({"enabled": 1})
    except Exception:
        return []

    names: list[str] = []
    for record in records:
        name = str(record.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _build_prompt(preamble: str, names: list[str]) -> str:
    name_list = "\n".join(f"- {name}" for name in names)
    return (
        "请根据以下合同首部内容，判断该合同属于哪种类型。\n\n"
        f"可选合同类型清单（只能从以下选项中选择一个）：\n{name_list}\n\n"
        f"合同首部正文：\n{preamble}\n\n"
        "请只返回合同类型名称，不要返回任何其他内容。"
    )


def _call_llm(prompt: str, settings: Settings) -> str | None:
    request_headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    request_body = {
        "model": settings.llm_model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    _write_llm_log(
        settings,
        "llm.request",
        {
            "method": "POST",
            "url": str(settings.llm_api_url),
            "headers": _safe_request_headers(request_headers),
            "body": request_body,
            "timeout": settings.llm_classify_timeout,
        },
    )
    started_at = time.perf_counter()
    try:
        response = httpx.post(
            str(settings.llm_api_url),
            headers=request_headers,
            json=request_body,
            timeout=settings.llm_classify_timeout,
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _write_llm_log(
            settings,
            "llm.response",
            {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "elapsed_ms": elapsed_ms,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        _write_llm_log(
            settings,
            "llm.content",
            {
                "content": content,
            },
        )
        return content
    except Exception as exc:
        logger.exception("LLM contract type classification failed")
        _write_llm_log(
            settings,
            "llm.error",
            {
                "error_type": type(exc).__name__,
                "message": traceback.format_exc().strip(),
            },
        )
        return None


def _confidence_from_response(raw: str, matched: str) -> int:
    if raw == matched:
        return 96
    if raw.startswith(matched):
        return 85
    return 70


def _content_texts(node: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    content = node.get("content")
    if not isinstance(content, list):
        return texts
    for item in content:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
    return texts


def _safe_request_headers(headers: dict[str, str]) -> dict[str, str]:
    result = dict(headers)
    if "Authorization" in result:
        result["Authorization"] = "Bearer ***"
    return result


def _write_llm_log(settings: Settings, event: str, payload: dict[str, Any]) -> None:
    if not settings.llm_classify_log_enabled:
        return
    try:
        path = settings.llm_classify_log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": event,
            "payload": payload,
        }
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        logger.exception("Failed to write LLM classification log")
