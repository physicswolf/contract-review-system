from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


def contract_to_frontend(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "name": record.get("contract_name", ""),
        "partyA": record.get("party_a", ""),
        "partyB": record.get("party_b", ""),
        "type": record.get("contract_type", "未分类"),
        "risk": record.get("risk", "未审核"),
        "riskCount": int(record.get("risk_count") or 0),
        "riskLevel": record.get("risk_level", "green"),
        "updatedAt": _format_dt(record.get("review_time") or record.get("updated_at")),
    }


def contract_from_frontend(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "name" in payload:
        result["contract_name"] = payload["name"]
    if "partyA" in payload:
        result["party_a"] = payload["partyA"]
    if "partyB" in payload:
        result["party_b"] = payload["partyB"]
    if "type" in payload:
        result["contract_type"] = payload["type"]
    return result


def user_to_frontend(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "account": record.get("account", ""),
        "name": record.get("name", ""),
        "company": record.get("company", ""),
        "role": record.get("role", ""),
        "phone": record.get("phone", ""),
        "email": record.get("email", ""),
    }


def dimension_to_frontend(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "name": record.get("name", ""),
        "desc": record.get("desc") or "",
        "status": record.get("status", "已启用"),
        "updatedAt": _format_dt(record.get("updated_at")),
    }


def point_to_frontend(record: dict[str, Any], *, detail: bool = False) -> dict[str, Any]:
    item = {
        "id": str(record["id"]),
        "name": record.get("name", ""),
        "category": record.get("category", ""),
        "dimension": record.get("dim_name", ""),
        "desc": record.get("desc") or "",
        "riskPoints": int(record.get("risk_points_count") or 0),
        "status": record.get("status", "已启用"),
        "defaultChecked": bool(record.get("default_checked", 1)),
        "updatedAt": _format_dt(record.get("updated_at")),
    }
    item["note"] = record.get("instruction") or ""
    if detail:
        item.update(
            {
                "dimId": str(record.get("dim_id") or ""),
                "risks": _json_value(record.get("risk_points"), []),
                "def": _json_value(record.get("default_result"), {}),
                "examples": _json_value(record.get("examples"), []),
            }
        )
    return item


def point_from_frontend(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    mapping = {
        "name": "name",
        "category": "category",
        "desc": "desc",
        "instruction": "instruction",
        "status": "status",
        "defaultChecked": "default_checked",
        "dimId": "dim_id",
        "dimension": "dimension",
    }
    for frontend_key, db_key in mapping.items():
        if frontend_key in payload:
            result[db_key] = payload[frontend_key]

    if "note" in payload:
        result["instruction"] = payload["note"]
    elif "instruction" in payload:
        result["instruction"] = payload["instruction"]

    if "risks" in payload:
        result["risk_points"] = payload["risks"]
    elif "riskPointsDetail" in payload:
        result["risk_points"] = payload["riskPointsDetail"]

    if "def" in payload:
        result["default_result"] = payload["def"]
    elif "defaultResult" in payload:
        result["default_result"] = payload["defaultResult"]

    if "examples" in payload:
        result["examples"] = payload["examples"]
    return result


def contract_type_to_frontend(record: dict[str, Any], *, detail: bool = False) -> dict[str, Any]:
    item = {
        "id": str(record["id"]),
        "code": record.get("code") or "",
        "name": record.get("name", ""),
        "stance": record.get("stance", ""),
        "desc": record.get("desc") or "",
        "keywords": _keywords_for_frontend(record.get("keywords")),
        "relatedPoints": int(record.get("related_points") or 0),
        "status": record.get("status", "已启用"),
        "updatedAt": _format_dt(record.get("updated_at")),
    }
    if detail:
        item["pointIds"] = [str(value) for value in record.get("point_ids", [])]
    return item


def contract_type_from_frontend(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    mapping = {
        "code": "code",
        "name": "name",
        "stance": "stance",
        "desc": "desc",
        "status": "status",
        "relatedPoints": "related_points",
        "pointIds": "point_ids",
    }
    for frontend_key, db_key in mapping.items():
        if frontend_key in payload:
            result[db_key] = payload[frontend_key]
    if "keywords" in payload:
        result["keywords"] = payload["keywords"]
    return result


def audit_result_to_frontend(
    *,
    contract: dict[str, Any],
    original_text: list[dict[str, str]],
    dimensions: list[str],
    risks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "contractId": str(contract["id"]),
        "contractName": contract.get("contract_name", ""),
        "partyA": contract.get("party_a", ""),
        "partyB": contract.get("party_b", ""),
        "docType": _doc_type(contract.get("file_id", "")),
        "originalText": original_text,
        "dimensions": dimensions,
        "risks": risks,
    }


def _format_dt(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _keywords_for_frontend(value: Any) -> str:
    parsed = _json_value(value, value)
    if isinstance(parsed, list):
        return ",".join(str(item) for item in parsed)
    return str(parsed or "")


def _doc_type(file_id: str) -> str:
    return "Word" if file_id else "Word"
