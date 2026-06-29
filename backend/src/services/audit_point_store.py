from __future__ import annotations

import json
from typing import Any

import pymysql

from src.services.db_base import db_pool
from src.services.dimension_store import dimension_repository


class AuditPointRepository:
    def find_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self._find_rows(filters or {}, detail=False)

    def count(self, filters: dict[str, Any] | None = None) -> int:
        return len(self.find_all(filters))

    def find_by_id(self, point_id: int) -> dict[str, Any] | None:
        rows = self._find_rows({"id": point_id}, detail=True)
        return rows[0] if rows else None

    def find_all_tmp_format(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [_point_tmp(row, detail=False) for row in self.find_all(filters)]

    def find_by_id_tmp_format(self, point_id: int) -> dict[str, Any] | None:
        row = self.find_by_id(point_id)
        return _point_tmp(row, detail=True) if row is not None else None

    def find_enabled_by_contract_type(self, type_id: int) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ap.id,
                               ap.dim_id,
                               d.name AS dim_name,
                               ap.name,
                               ap.description,
                               ap.instruction,
                               ap.risk_points,
                               ap.examples,
                               ap.default_result,
                               ap.enabled,
                               ap.sort_order,
                               ap.updated_at
                          FROM contract_type_audit_point ctap
                          JOIN audit_point ap ON ap.id = ctap.audit_point_id
                          JOIN dimension d ON d.id = ap.dim_id
                         WHERE ctap.contract_type_id = %(type_id)s
                           AND ctap.enabled = 1
                           AND ap.enabled = 1
                           AND ap.deleted_at IS NULL
                         ORDER BY ctap.sort_order ASC, ctap.id ASC
                        """,
                        {"type_id": type_id},
                    )
                    return [_with_aliases(dict(row), detail=True) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型审查点读取失败: {exc}") from exc

    def insert(self, payload: dict[str, Any]) -> int:
        data = self._payload(payload)
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_point (
                            dim_id, name, description, instruction,
                            risk_points, examples, default_result,
                            enabled, sort_order
                        )
                        VALUES (
                            %(dim_id)s, %(name)s, %(description)s, %(instruction)s,
                            %(risk_points)s, %(examples)s, %(default_result)s,
                            %(enabled)s, %(sort_order)s
                        )
                        """,
                        data,
                    )
                    point_id = int(cursor.lastrowid)
                conn.commit()
                return point_id
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点创建失败: {exc}") from exc

    def insert_from_tmp(self, payload: dict[str, Any]) -> int:
        return self.insert(payload)

    def update_by_id(self, point_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        data = self._payload(updates, partial=True)
        if not data:
            return self.find_by_id(point_id)

        assignments = ", ".join(f"{key} = %({key})s" for key in data)
        data["id"] = point_id
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE audit_point SET {assignments} WHERE id = %(id)s AND deleted_at IS NULL",
                        data,
                    )
                    if cursor.rowcount == 0:
                        return None
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点更新失败: {exc}") from exc
        return self.find_by_id(point_id)

    def update_from_tmp(self, point_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self.update_by_id(point_id, payload)

    def toggle_enabled(self, point_id: int, enabled: bool) -> dict[str, Any] | None:
        return self.update_by_id(point_id, {"enabled": 1 if enabled else 0})

    def delete_by_id(self, point_id: int) -> bool:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE audit_point SET deleted_at = NOW() WHERE id = %(id)s AND deleted_at IS NULL",
                        {"id": point_id},
                    )
                    deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点删除失败: {exc}") from exc

    def _find_rows(self, filters: dict[str, Any], *, detail: bool) -> list[dict[str, Any]]:
        keyword = str(filters.get("keyword") or "").strip()
        point_id = filters.get("id")
        dim_id = filters.get("dim_id")
        enabled = filters.get("enabled")
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ap.id,
                               ap.dim_id,
                               d.name AS dim_name,
                               ap.name,
                               ap.description,
                               ap.instruction,
                               ap.risk_points,
                               ap.examples,
                               ap.default_result,
                               ap.enabled,
                               ap.sort_order,
                               ap.created_at,
                               ap.updated_at,
                               COALESCE(JSON_LENGTH(ap.risk_points), 0) AS risk_points_count
                          FROM audit_point ap
                          JOIN dimension d ON d.id = ap.dim_id
                         WHERE ap.deleted_at IS NULL
                           AND (%(id)s IS NULL OR ap.id = %(id)s)
                           AND (%(keyword)s = '' OR ap.name LIKE CONCAT('%%', %(keyword)s, '%%'))
                           AND (%(dim_id)s IS NULL OR ap.dim_id = %(dim_id)s)
                           AND (%(enabled)s IS NULL OR ap.enabled = %(enabled)s)
                         ORDER BY ap.sort_order ASC, ap.id ASC
                        """,
                        {
                            "id": _int_or_none(point_id),
                            "keyword": keyword,
                            "dim_id": _int_or_none(dim_id),
                            "enabled": _int_or_none(enabled),
                        },
                    )
                    return [_with_aliases(dict(row), detail=detail) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点读取失败: {exc}") from exc

    def _payload(self, payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if "dimId" in payload or "dim_id" in payload or "dimension" in payload or not partial:
            result["dim_id"] = _resolve_dim_id(payload)
        if "name" in payload:
            result["name"] = str(payload.get("name") or "").strip()
        elif not partial:
            result["name"] = ""
        if "description" in payload or "desc" in payload:
            result["description"] = str(payload.get("description") or payload.get("desc") or "")
        elif not partial:
            result["description"] = ""
        if "instruction" in payload or "note" in payload:
            result["instruction"] = str(payload.get("instruction") or payload.get("note") or "")
        elif not partial:
            result["instruction"] = ""
        if "enabled" in payload:
            result["enabled"] = _enabled_value(payload.get("enabled"))
        elif "status" in payload:
            result["enabled"] = 1 if payload.get("status") == "已启用" else 0
        elif not partial:
            result["enabled"] = 1
        if "sortOrder" in payload or "sort_order" in payload:
            result["sort_order"] = int(payload.get("sortOrder") or payload.get("sort_order") or 0)
        elif not partial:
            result["sort_order"] = 0

        if "riskPoints" in payload or "risk_points" in payload or "risks" in payload:
            result["risk_points"] = _json_dump(
                _normalize_risk_points(
                    payload.get("riskPoints")
                    if "riskPoints" in payload
                    else payload.get("risk_points", payload.get("risks"))
                ),
                [],
            )
        elif not partial:
            result["risk_points"] = _json_dump([], [])

        if "examples" in payload:
            result["examples"] = _json_dump(_normalize_examples(payload.get("examples")), [])
        elif not partial:
            result["examples"] = _json_dump([], [])

        if "defaultResult" in payload or "default_result" in payload or "def" in payload:
            result["default_result"] = _json_dump(
                _normalize_default_result(
                    payload.get("defaultResult")
                    if "defaultResult" in payload
                    else payload.get("default_result", payload.get("def"))
                ),
                {},
            )
        elif not partial:
            result["default_result"] = _json_dump({}, {})

        return result


def _resolve_dim_id(payload: dict[str, Any]) -> int:
    dim_id = payload.get("dimId", payload.get("dim_id"))
    if dim_id not in (None, ""):
        return int(dim_id)

    name = str(payload.get("dimension") or "").strip()
    if name:
        record = dimension_repository.find_by_name(name)
        if record is not None:
            return int(record["id"])

    names = dimension_repository.find_all()
    if names:
        return int(names[0]["id"])
    raise ValueError("请先创建审核维度")


def _json_dump(value: Any, fallback: Any) -> str:
    if value in (None, ""):
        value = fallback
    return json.dumps(value, ensure_ascii=False)


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback


def _point_tmp(row: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    risk_points = _json_value(row.get("risk_points"), [])
    item = {
        "id": int(row["id"]),
        "name": row.get("name", ""),
        "description": row.get("description") or "",
        "instruction": row.get("instruction") or "",
        "dimId": int(row.get("dim_id") or 0),
        "dimName": row.get("dim_name") or "",
        "riskPoints": _risk_point_names(risk_points),
        "enabled": _enabled_value(row.get("enabled", 1)),
        "sortOrder": int(row.get("sort_order") or 0),
        "updatedAt": _format_iso(row.get("updated_at")),
    }
    if detail:
        item["riskPoints"] = risk_points
        item["examples"] = _json_value(row.get("examples"), [])
        item["defaultResult"] = _json_value(row.get("default_result"), {})
    return item


def _with_aliases(row: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    enabled = _enabled_value(row.get("enabled", 1))
    row["enabled"] = enabled
    row["desc"] = row.get("description") or ""
    row["status"] = "已启用" if enabled else "已停用"
    row["category"] = ""
    row["default_checked"] = enabled
    if "risk_points_count" not in row:
        risk_points = _json_value(row.get("risk_points"), [])
        row["risk_points_count"] = len(risk_points) if isinstance(risk_points, list) else 0
    return row


def _risk_point_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("title") or "").strip()
            if name:
                names.append(name)
    return names


def _normalize_risk_points(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "name": str(item.get("name") or item.get("title") or ""),
                "highStd": str(item.get("highStd") or item.get("high") or ""),
                "lowStd": str(item.get("lowStd") or item.get("low") or ""),
                "noneStd": str(item.get("noneStd") or ""),
            }
        )
    return result


def _normalize_default_result(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        "level": str(value.get("level") or "高风险"),
        "riskPointName": str(value.get("riskPointName") or ""),
        "analysis": str(value.get("analysis") or value.get("overview") or ""),
        "suggestion": str(value.get("suggestion") or value.get("solution") or ""),
    }


def _normalize_examples(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "original": str(item.get("original") or item.get("clause") or ""),
                "level": str(item.get("level") or "高风险"),
                "riskPointName": str(item.get("riskPointName") or ""),
                "analysis": str(item.get("analysis") or item.get("overview") or ""),
                "suggestion": str(item.get("suggestion") or item.get("solution") or ""),
            }
        )
    return result


def _int_or_none(value: Any) -> int | None:
    return None if value in (None, "") else int(value)


def _enabled_value(value: Any) -> int:
    return 1 if int(value or 0) else 0


def _format_iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


audit_point_repository = AuditPointRepository()
