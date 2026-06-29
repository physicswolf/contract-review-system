from __future__ import annotations

import json
from typing import Any

import pymysql

from src.services.db_base import db_pool


class ContractTypeRepository:
    def find_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        keyword = str((filters or {}).get("keyword") or "").strip()
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT *
                          FROM contract_type
                         WHERE deleted_at IS NULL
                           AND (
                                %(keyword)s = ''
                                OR name LIKE CONCAT('%%', %(keyword)s, '%%')
                                OR code LIKE CONCAT('%%', %(keyword)s, '%%')
                           )
                         ORDER BY id ASC
                        """,
                        {"keyword": keyword},
                    )
                    return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型列表读取失败: {exc}") from exc

    def count(self, filters: dict[str, Any] | None = None) -> int:
        return len(self.find_all(filters))

    def find_by_id(self, type_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM contract_type WHERE id = %(id)s AND deleted_at IS NULL",
                        {"id": type_id},
                    )
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    record = dict(row)
                    cursor.execute(
                        """
                        SELECT audit_point_id
                          FROM contract_type_audit_point
                         WHERE contract_type_id = %(id)s AND enabled = 1
                         ORDER BY sort_order ASC, id ASC
                        """,
                        {"id": type_id},
                    )
                    record["point_ids"] = [row["audit_point_id"] for row in cursor.fetchall()]
                    return record
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型读取失败: {exc}") from exc

    def insert(self, payload: dict[str, Any]) -> int:
        data = _payload(payload)
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO contract_type (
                            code, name, stance, `desc`, keywords, related_points, status
                        )
                        VALUES (
                            %(code)s, %(name)s, %(stance)s, %(desc)s,
                            %(keywords)s, %(related_points)s, %(status)s
                        )
                        """,
                        data,
                    )
                    type_id = int(cursor.lastrowid)
                    _replace_associations(cursor, type_id, payload.get("point_ids"))
                conn.commit()
                return type_id
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型创建失败: {exc}") from exc

    def update_by_id(self, type_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        data = _payload(updates, partial=True)
        point_ids = updates.get("point_ids")
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    if data:
                        assignments = ", ".join(
                            f"`{key}` = %({key})s" if key == "desc" else f"{key} = %({key})s"
                            for key in data
                        )
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
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同类型更新失败: {exc}") from exc
        return self.find_by_id(type_id)

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


def _payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    defaults = {
        "code": "",
        "name": "",
        "stance": "",
        "desc": "",
        "keywords": [],
        "related_points": 0,
        "status": "已启用",
    }
    for key, default in defaults.items():
        if key not in payload:
            if not partial:
                payload[key] = default
            else:
                continue
        value = payload.get(key)
        if key == "keywords":
            if isinstance(value, str):
                value = [part.strip() for part in value.split(",") if part.strip()]
            result[key] = json.dumps(value or [], ensure_ascii=False)
        elif key == "related_points":
            result[key] = int(value or 0)
        else:
            result[key] = str(value or "")
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


contract_type_repository = ContractTypeRepository()
