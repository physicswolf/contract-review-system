from __future__ import annotations

import json
from typing import Any

import pymysql

from src.services.db_base import db_pool


class ContractTypeRepository:
    def find_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self._find_all(filters or {})

    def find_all_tmp(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [_contract_type_tmp(row, detail=False) for row in self.find_all(filters)]

    def count(self, filters: dict[str, Any] | None = None) -> int:
        return len(self.find_all(filters))

    def find_by_id(self, type_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ct.*,
                               (
                                   SELECT COUNT(*)
                                     FROM contract_type_audit_point ctap
                                    WHERE ctap.contract_type_id = ct.id
                                      AND ctap.enabled = 1
                               ) AS linked_point_count
                          FROM contract_type ct
                         WHERE ct.id = %(id)s AND ct.deleted_at IS NULL
                        """,
                        {"id": type_id},
                    )
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    record = _with_aliases(dict(row), detail=True)
                    cursor.execute(
                        """
                        SELECT audit_point_id, enabled
                          FROM contract_type_audit_point
                         WHERE contract_type_id = %(id)s
                         ORDER BY sort_order ASC, id ASC
                        """,
                        {"id": type_id},
                    )
                    linked = [dict(item) for item in cursor.fetchall()]
                    record["linked_audit_points"] = linked
                    record["point_ids"] = [
                        item["audit_point_id"] for item in linked if int(item.get("enabled") or 0) == 1
                    ]
                    return record
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型读取失败: {exc}") from exc

    def find_by_id_tmp(self, type_id: int) -> dict[str, Any] | None:
        row = self.find_by_id(type_id)
        return _contract_type_tmp(row, detail=True) if row is not None else None

    def find_by_name_stance(self, name: str, stance: str) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, code, name, stance, description, keywords, enabled, updated_at
                          FROM contract_type
                         WHERE name = %(name)s
                           AND stance = %(stance)s
                           AND enabled = 1
                           AND deleted_at IS NULL
                        """,
                        {"name": name, "stance": stance},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型匹配失败: {exc}") from exc
        return _with_aliases(dict(row), detail=False) if row is not None else None

    def insert(self, payload: dict[str, Any]) -> int:
        data = _payload(payload)
        point_ids = payload.get("point_ids") or payload.get("auditPointIds")
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO contract_type (code, name, stance, description, keywords, enabled)
                        VALUES (%(code)s, %(name)s, %(stance)s, %(description)s, %(keywords)s, %(enabled)s)
                        """,
                        data,
                    )
                    type_id = int(cursor.lastrowid)
                    _replace_associations(cursor, type_id, point_ids)
                conn.commit()
                return type_id
            finally:
                conn.close()
        except pymysql.err.IntegrityError as exc:
            raise ValueError("该合同类型-立场已存在") from exc
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型创建失败: {exc}") from exc

    def insert_from_tmp(self, payload: dict[str, Any]) -> int:
        return self.insert(payload)

    def update_by_id(self, type_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        data = _payload(updates, partial=True)
        point_ids = updates.get("point_ids", updates.get("auditPointIds"))
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    if data:
                        assignments = ", ".join(f"{key} = %({key})s" for key in data)
                        data["id"] = type_id
                        cursor.execute(
                            f"UPDATE contract_type SET {assignments} WHERE id = %(id)s AND deleted_at IS NULL",
                            data,
                        )
                        if cursor.rowcount == 0:
                            return None
                    if point_ids is not None:
                        _replace_associations(cursor, type_id, point_ids)
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.IntegrityError as exc:
            raise ValueError("该合同类型-立场已存在") from exc
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型更新失败: {exc}") from exc
        return self.find_by_id(type_id)

    def update_from_tmp(self, type_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self.update_by_id(type_id, payload)

    def delete_by_id(self, type_id: int) -> bool:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE contract_type SET deleted_at = NOW() WHERE id = %(id)s AND deleted_at IS NULL",
                        {"id": type_id},
                    )
                    deleted = cursor.rowcount > 0
                    cursor.execute(
                        "DELETE FROM contract_type_audit_point WHERE contract_type_id = %(id)s",
                        {"id": type_id},
                    )
                conn.commit()
                return deleted
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型删除失败: {exc}") from exc

    def replace_associations(self, type_id: int, point_ids: list[int]) -> None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    _replace_associations(cursor, type_id, point_ids)
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型审查点关联保存失败: {exc}") from exc

    def toggle_association(self, type_id: int, point_id: int, enabled: bool) -> None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE contract_type_audit_point
                           SET enabled = %(enabled)s
                         WHERE contract_type_id = %(type_id)s
                           AND audit_point_id = %(point_id)s
                        """,
                        {"type_id": type_id, "point_id": point_id, "enabled": 1 if enabled else 0},
                    )
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型审查点启停失败: {exc}") from exc

    def _find_all(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        keyword = str(filters.get("keyword") or "").strip()
        enabled = filters.get("enabled")
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ct.*,
                               COUNT(ctap.audit_point_id) AS linked_point_count
                          FROM contract_type ct
                          LEFT JOIN contract_type_audit_point ctap
                            ON ctap.contract_type_id = ct.id
                           AND ctap.enabled = 1
                         WHERE ct.deleted_at IS NULL
                           AND (
                                %(keyword)s = ''
                                OR ct.name LIKE CONCAT('%%', %(keyword)s, '%%')
                                OR ct.code LIKE CONCAT('%%', %(keyword)s, '%%')
                           )
                           AND (%(enabled)s IS NULL OR ct.enabled = %(enabled)s)
                         GROUP BY ct.id
                         ORDER BY ct.id ASC
                        """,
                        {
                            "keyword": keyword,
                            "enabled": _int_or_none(enabled),
                        },
                    )
                    return [_with_aliases(dict(row), detail=False) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型列表读取失败: {exc}") from exc


def _payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("code", "name", "stance"):
        if key in payload:
            result[key] = str(payload.get(key) or "")
        elif not partial:
            result[key] = ""

    if "description" in payload or "desc" in payload:
        result["description"] = str(payload.get("description") or payload.get("desc") or "")
    elif not partial:
        result["description"] = ""

    if "keywords" in payload:
        value = payload.get("keywords")
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",") if part.strip()]
        result["keywords"] = json.dumps(value or [], ensure_ascii=False)
    elif not partial:
        result["keywords"] = json.dumps([], ensure_ascii=False)

    if "enabled" in payload:
        result["enabled"] = 1 if int(payload.get("enabled") or 0) else 0
    elif "status" in payload:
        result["enabled"] = 1 if payload.get("status") == "已启用" else 0
    elif not partial:
        result["enabled"] = 1

    return result


def _replace_associations(cursor: Any, type_id: int, point_ids: Any) -> None:
    if point_ids is None:
        return
    cursor.execute(
        "DELETE FROM contract_type_audit_point WHERE contract_type_id = %(id)s",
        {"id": type_id},
    )
    for index, point_id in enumerate(point_ids):
        cursor.execute(
            """
            INSERT INTO contract_type_audit_point (
                contract_type_id, audit_point_id, enabled, sort_order
            )
            VALUES (%(type_id)s, %(point_id)s, 1, %(sort_order)s)
            """,
            {"type_id": type_id, "point_id": int(point_id), "sort_order": index},
        )


def _contract_type_tmp(record: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    item = {
        "id": int(record["id"]),
        "code": record.get("code") or "",
        "name": record.get("name", ""),
        "stance": record.get("stance", ""),
        "description": record.get("description") or "",
        "keywords": _json_value(record.get("keywords"), []),
        "enabled": 1 if int(record.get("enabled") or 0) else 0,
        "linkedPointCount": int(record.get("linked_point_count") or 0),
        "updatedAt": _format_iso(record.get("updated_at")),
    }
    if detail:
        item["linkedAuditPoints"] = [
            {"auditPointId": int(row["audit_point_id"]), "enabled": int(row.get("enabled") or 0)}
            for row in record.get("linked_audit_points", [])
        ]
    return item


def _with_aliases(record: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    enabled = 1 if int(record.get("enabled") or 0) else 0
    record["enabled"] = enabled
    record["desc"] = record.get("description") or ""
    record["status"] = "已启用" if enabled else "已停用"
    record["related_points"] = int(record.get("linked_point_count") or 0)
    return record


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback


def _int_or_none(value: Any) -> int | None:
    return None if value in (None, "") else int(value)


def _format_iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


contract_type_repository = ContractTypeRepository()
