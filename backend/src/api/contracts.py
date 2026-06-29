from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse

from src.api.adapters import (
    audit_result_to_frontend,
    contract_from_frontend,
    contract_to_frontend,
)
from src.api.responses import error_response, flat_list, flat_object, ok_deleted
from src.config import get_settings
from src.pipelines.document_upload import (
    DOCUMENT_UPLOAD_PIPELINE_ERRORS,
    DocumentUploadPipeline,
)
from src.pipelines.document_tasks import document_task_manager
from src.services.audit_point_store import audit_point_repository
from src.services.audit_result_store import audit_result_store
from src.services.contract_extractor import extract_contract_meta
from src.services.contract_store import get_contract_repository
from src.services.file_storage import UploadError
from src.services.structure_editor import load_document_json


router = APIRouter()
SHANGHAI_TZ = timezone(timedelta(hours=8))


@router.get("")
async def list_contracts(
    name: str = Query(default="", description="合同名称（模糊搜索）"),
    partyA: str = Query(default="", description="甲方（模糊搜索）"),
    partyB: str = Query(default="", description="乙方（模糊搜索）"),
    contract_name: str = Query(default="", description="兼容后端字段"),
    party_a: str = Query(default="", description="兼容后端字段"),
    party_b: str = Query(default="", description="兼容后端字段"),
    contract_type: str = Query(default="", description="合同类型（模糊搜索）"),
) -> JSONResponse:
    filters = {
        "contract_name": name or contract_name,
        "party_a": partyA or party_a,
        "party_b": partyB or party_b,
        "contract_type": contract_type,
    }
    try:
        repository = get_contract_repository()
        records = repository.find_all(filters)
        total = repository.count(filters)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同列表读取失败")

    return flat_list([contract_to_frontend(record) for record in records], total)


@router.post("", status_code=201)
async def create_contract(payload: dict[str, Any]) -> JSONResponse:
    now = _now_iso()
    record = {
        **contract_from_frontend(payload),
        "file_id": str(payload.get("fileId") or payload.get("file_id") or ""),
        "review_time": str(payload.get("reviewTime") or payload.get("review_time") or now),
        "created_at": now,
        "updated_at": now,
    }
    if not record["file_id"]:
        return error_response(422, "FILE_ID_REQUIRED", "请提供文件 ID")

    try:
        repository = get_contract_repository()
        contract_id = repository.insert(record)
        created = repository.find_by_id(contract_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同创建失败")

    return flat_object(contract_to_frontend(created), status_code=201)


@router.post("/upload")
async def upload_contract(file: UploadFile | None = File(default=None)) -> JSONResponse:
    if file is None:
        return error_response(422, "FILE_REQUIRED", "请提交合同文件")

    settings = get_settings()
    try:
        result = await DocumentUploadPipeline(settings).run(file)
        task = await _wait_for_task(result.task.id)
    except DOCUMENT_UPLOAD_PIPELINE_ERRORS as exc:
        return _upload_error_response(exc)

    if task is None:
        return error_response(500, "DOCUMENT_TASK_TIMEOUT", "文档解析超时")
    if task.status == "failed":
        message = task.error.message if task.error else "文档解析失败"
        return error_response(500, "DOCUMENT_TASK_FAILED", message)

    try:
        repository = get_contract_repository()
        record = repository.find_by_file_id(result.metadata.id)
        if record is None:
            contract_id = repository.upsert_by_file_id(
                extract_contract_meta(result.metadata.id, settings)
            )
            record = repository.find_by_id(contract_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同记录保存失败")

    if record is None:
        return error_response(500, "INTERNAL_ERROR", "合同记录保存失败")

    return flat_object(
        {
            "id": str(record["id"]),
            "name": record.get("contract_name") or result.metadata.original_name,
            "detectedType": record.get("contract_type") or "未分类",
            "matchConfidence": 96 if record.get("contract_type") != "未分类" else 50,
            "fileId": result.metadata.id,
            "enableStructureEditor": settings.enable_structure_editor,
        }
    )


@router.post("/{contract_id}/audit")
async def start_audit(contract_id: int, payload: dict[str, Any]) -> JSONResponse:
    role = str(payload.get("role") or "甲方")
    point_ids = [int(point_id) for point_id in payload.get("points") or []]
    if not point_ids:
        return error_response(422, "POINTS_REQUIRED", "请至少选择一个审核点")

    try:
        repository = get_contract_repository()
        contract = repository.find_by_id(contract_id)
        if contract is None:
            return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")

        points = [
            point
            for point_id in point_ids
            if (point := audit_point_repository.find_by_id(point_id)) is not None
        ]
        if not points:
            return error_response(422, "POINTS_REQUIRED", "未找到可用审核点")

        task_id = audit_result_store.create_task(contract_id, role)
        original_blocks = _original_text_for_contract(contract, [])
        items = _build_audit_items(points, original_blocks)
        stats = _build_dimension_stats(items)
        audit_result_store.insert_results(task_id, items)
        audit_result_store.insert_stats(task_id, stats)
        major_count = sum(1 for item in items if item["risk_level"] == 1)
        general_count = len(items) - major_count
        audit_result_store.complete_task(
            task_id,
            total=len(items),
            major=major_count,
            general=general_count,
        )
        risk, risk_level = _risk_summary(major_count, general_count)
        repository.update_risk_cache(
            contract_id,
            risk=risk,
            risk_count=len(items),
            risk_level=risk_level,
        )
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审核执行失败")

    return flat_object({"id": str(contract_id), "status": "done"})


@router.get("/{contract_id}/result")
async def get_audit_result(contract_id: int) -> JSONResponse:
    try:
        contract = get_contract_repository().find_by_id(contract_id)
        if contract is None:
            return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")
        task = audit_result_store.get_latest_task_by_contract(contract_id)
        if task is None:
            return error_response(404, "AUDIT_RESULT_NOT_FOUND", "尚未生成审核结果")
        rows = audit_result_store.get_results_by_task(int(task["id"]))
        stats = audit_result_store.get_stats_by_task(int(task["id"]))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审核结果读取失败")

    risks = [_risk_to_frontend(row) for row in rows]
    dimensions = [str(row["dim_name"]) for row in stats] or _dimension_order(risks)
    highlights = [str(row.get("hit_text") or "") for row in rows if row.get("hit_text")]
    original_text = _original_text_for_contract(contract, highlights)
    return flat_object(
        audit_result_to_frontend(
            contract=contract,
            original_text=original_text,
            dimensions=dimensions,
            risks=risks,
        )
    )


@router.get("/{contract_id}")
async def get_contract_detail(contract_id: int) -> JSONResponse:
    try:
        record = get_contract_repository().find_by_id(contract_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同详情读取失败")

    if record is None:
        return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")
    return flat_object(contract_to_frontend(record))


@router.put("/{contract_id}")
async def update_contract(contract_id: int, payload: dict[str, Any]) -> JSONResponse:
    updates = contract_from_frontend(payload)
    if updates:
        updates["updated_at"] = _now_iso()

    try:
        record = get_contract_repository().update_by_id(contract_id, updates)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同更新失败")

    if record is None:
        return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")
    return flat_object(contract_to_frontend(record))


@router.delete("/{contract_id}")
async def delete_contract(contract_id: int) -> JSONResponse:
    try:
        repository = get_contract_repository()
        record = repository.find_by_id(contract_id)
        if record is None:
            return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")
        deleted = repository.delete_by_id(contract_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同删除失败")

    if not deleted:
        return error_response(404, "CONTRACT_NOT_FOUND", "合同不存在")

    _delete_contract_files(record["file_id"])
    return ok_deleted()


async def _wait_for_task(task_id: str, *, attempts: int = 900) -> Any | None:
    for _ in range(attempts):
        task = document_task_manager.get(task_id)
        if task is not None and task.status in {"succeeded", "failed"}:
            return task
        await asyncio.sleep(0.1)
    return None


def _upload_error_response(error: UploadError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message)


def _build_audit_items(
    points: list[dict[str, Any]],
    original_blocks: list[dict[str, str]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        default_result = _json_value(point.get("default_result"), {})
        risk_points = _json_value(point.get("risk_points"), [])
        level = _frontend_level(default_result)
        hit_text = _pick_hit_text(original_blocks, point)
        items.append(
            {
                "dim_id": int(point["dim_id"]),
                "dim_name": str(point.get("dim_name") or ""),
                "audit_point_id": int(point["id"]),
                "title": str(point.get("name") or "合同风险"),
                "risk_level": 1 if level == "major" else 2,
                "risk_summary": str(
                    default_result.get("analysis")
                    or default_result.get("overview")
                    or point.get("description")
                    or point.get("desc")
                    or "该条款存在潜在风险。"
                ),
                "risk_analysis": str(
                    _risk_point_analysis(risk_points, level)
                    or default_result.get("analysis")
                    or default_result.get("overview")
                    or "建议结合业务背景进一步核查。"
                ),
                "modify_example": str(
                    default_result.get("suggestion")
                    or default_result.get("solution")
                    or "建议补充明确约定，降低履约和争议风险。"
                ),
                "clause_name": str(
                    default_result.get("clause") or point.get("name") or ""
                ),
                "hit_text": hit_text,
                "sort_order": index,
            }
        )
    return items


def _build_dimension_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for item in items:
        dim_id = int(item["dim_id"])
        stat = grouped.setdefault(
            dim_id,
            {
                "dim_id": dim_id,
                "dim_name": item["dim_name"],
                "total_count": 0,
                "major_count": 0,
                "general_count": 0,
            },
        )
        stat["total_count"] += 1
        if item["risk_level"] == 1:
            stat["major_count"] += 1
        else:
            stat["general_count"] += 1
    return list(grouped.values())


def _risk_to_frontend(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "dimension": row.get("dim_name", ""),
        "title": row.get("title", ""),
        "level": "major" if int(row.get("risk_level") or 2) == 1 else "general",
        "desc": row.get("risk_summary") or "",
        "analysis": row.get("risk_analysis") or "",
        "example": row.get("modify_example") or "",
        "clause": row.get("clause_name") or "",
    }


def _original_text_for_contract(
    contract: dict[str, Any],
    highlights: list[str],
) -> list[dict[str, str]]:
    try:
        document = load_document_json(str(contract["file_id"]), get_settings())
    except Exception:
        return _fallback_original_text(contract)

    structure = document.get("contract_structure")
    if not isinstance(structure, dict):
        return _fallback_original_text(contract)

    blocks: list[dict[str, str]] = []
    title = str(contract.get("contract_name") or "")
    if title:
        blocks.append({"type": "h2", "text": title})
    _append_structure_blocks(structure, blocks, highlights)
    return blocks or _fallback_original_text(contract)


def _append_structure_blocks(
    node: dict[str, Any],
    blocks: list[dict[str, str]],
    highlights: list[str],
) -> None:
    title = str(node.get("title") or "").strip()
    if title and title.upper() != "ROOT":
        blocks.append({"type": _heading_type(node), "text": title})

    content = node.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    blocks.append({"type": _text_type(text, highlights), "text": text})

    for child in node.get("children") or []:
        if isinstance(child, dict):
            _append_structure_blocks(child, blocks, highlights)


def _fallback_original_text(contract: dict[str, Any]) -> list[dict[str, str]]:
    blocks = [{"type": "h2", "text": str(contract.get("contract_name") or "合同文本")}]
    if contract.get("party_a"):
        blocks.append({"type": "p", "text": f"甲方：{contract['party_a']}"})
    if contract.get("party_b"):
        blocks.append({"type": "p", "text": f"乙方：{contract['party_b']}"})
    return blocks


def _heading_type(node: dict[str, Any]) -> str:
    kind = str(node.get("kind") or "").lower()
    return "h2" if kind in {"chapter", "heading", "section"} else "h3"


def _text_type(text: str, highlights: list[str]) -> str:
    return "highlight" if any(mark and (mark in text or text in mark) for mark in highlights) else "p"


def _pick_hit_text(blocks: list[dict[str, str]], point: dict[str, Any]) -> str:
    candidates = [
        str(point.get("name") or ""),
        str(point.get("category") or ""),
        str(point.get("description") or ""),
        str(point.get("desc") or ""),
    ]
    for block in blocks:
        text = block.get("text", "")
        if any(candidate and candidate in text for candidate in candidates):
            return text
    for block in blocks:
        if block.get("type") == "p" and block.get("text"):
            return block["text"]
    return ""


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback


def _frontend_level(default_result: dict[str, Any]) -> str:
    value = str(default_result.get("level") or default_result.get("riskLevel") or "")
    if value in {"高风险", "重大风险", "major", "red"}:
        return "major"
    overview = str(default_result.get("analysis") or default_result.get("overview") or "")
    if any(kw in overview for kw in ["高风险", "重大风险", "严重", "可能无效"]):
        return "major"
    return "general"


def _risk_point_analysis(risk_points: Any, level: str) -> str:
    if not isinstance(risk_points, list):
        return ""
    preferred = "highStd" if level == "major" else "lowStd"
    fallback = "high" if level == "major" else "low"
    for item in risk_points:
        if isinstance(item, dict) and item.get(preferred):
            return str(item[preferred])
        if isinstance(item, dict) and item.get(fallback):
            return str(item[fallback])
    return ""


def _dimension_order(risks: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for risk in risks:
        dimension = str(risk.get("dimension") or "")
        if dimension and dimension not in result:
            result.append(dimension)
    return result


def _risk_summary(major_count: int, general_count: int) -> tuple[str, str]:
    if major_count:
        return "高风险", "red"
    if general_count:
        return "中风险", "amber"
    return "低风险", "green"


def _delete_contract_files(file_id: str) -> None:
    settings = get_settings()

    if settings.upload_root.exists():
        for path in settings.upload_root.rglob(f"{file_id}.*"):
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    shutil.rmtree(settings.parsing_root / file_id, ignore_errors=True)


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")
