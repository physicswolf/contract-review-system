from __future__ import annotations

from typing import Any

import pymysql

from src.services.db_base import db_pool


class DimensionRepository:
    def find_all(self, enabled: int | None = None) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, description, sort_order, enabled, created_at, updated_at
                          FROM dimension
                         WHERE (%(enabled)s IS NULL OR enabled = %(enabled)s)
                         ORDER BY sort_order ASC, id ASC
                        """,
                        {"enabled": _enabled_param(enabled)},
                    )
                    return [_with_aliases(dict(row)) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度列表读取失败: {exc}") from exc

    def count(self) -> int:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) AS total FROM dimension")
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度数量统计失败: {exc}") from exc
        return int(row["total"])

    def find_by_id(self, dimension_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, description, sort_order, enabled, created_at, updated_at
                          FROM dimension
                         WHERE id = %(id)s
                        """,
                        {"id": dimension_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度读取失败: {exc}") from exc
        return _with_aliases(dict(row)) if row is not None else None

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, description, sort_order, enabled, created_at, updated_at
                          FROM dimension
                         WHERE name = %(name)s
                        """,
                        {"name": name},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度读取失败: {exc}") from exc
        return _with_aliases(dict(row)) if row is not None else None

    def find_names(self) -> list[str]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT name
                          FROM dimension
                         WHERE enabled = 1
                         ORDER BY sort_order ASC, id ASC
                        """
                    )
                    return [str(row["name"]) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度名称读取失败: {exc}") from exc

    def find_selectable(self) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT name, description
                          FROM dimension
                         WHERE enabled = 1
                         ORDER BY sort_order ASC, id ASC
                        """
                    )
                    return [_with_aliases(dict(row)) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 可选维度读取失败: {exc}") from exc

    def insert(self, payload: dict[str, Any]) -> int:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO dimension (name, description, sort_order, enabled)
                        VALUES (%(name)s, %(description)s, %(sort_order)s, %(enabled)s)
                        """,
                        _payload(payload),
                    )
                    dimension_id = int(cursor.lastrowid)
                conn.commit()
                return dimension_id
            finally:
                conn.close()
        except pymysql.err.IntegrityError as exc:
            raise ValueError("维度名称已存在") from exc
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度创建失败: {exc}") from exc

    def update_by_id(self, dimension_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        payload = _payload(updates, partial=True)
        if not payload:
            return self.find_by_id(dimension_id)

        assignments = ", ".join(f"{key} = %({key})s" for key in payload)
        payload["id"] = dimension_id
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE dimension SET {assignments} WHERE id = %(id)s",
                        payload,
                    )
                    if cursor.rowcount == 0:
                        return None
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.IntegrityError as exc:
            raise ValueError("维度名称已存在") from exc
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度更新失败: {exc}") from exc
        return self.find_by_id(dimension_id)

    def delete_by_id(self, dimension_id: int) -> bool:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS total
                          FROM audit_point
                         WHERE dim_id = %(id)s AND deleted_at IS NULL
                        """,
                        {"id": dimension_id},
                    )
                    total = int(cursor.fetchone()["total"])
                    if total > 0:
                        raise ValueError(f"该维度下存在 {total} 个审查点，请先删除或迁移后再操作")
                    cursor.execute("DELETE FROM dimension WHERE id = %(id)s", {"id": dimension_id})
                    deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
            finally:
                conn.close()
        except ValueError:
            raise
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度删除失败: {exc}") from exc


def _payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "name" in payload:
        result["name"] = str(payload.get("name") or "").strip()
    elif not partial:
        result["name"] = ""

    if "description" in payload or "desc" in payload:
        result["description"] = str(payload.get("description") or payload.get("desc") or "")
    elif not partial:
        result["description"] = ""

    if "sortOrder" in payload or "sort_order" in payload:
        result["sort_order"] = int(payload.get("sortOrder") or payload.get("sort_order") or 0)
    elif not partial:
        result["sort_order"] = 0

    if "enabled" in payload:
        result["enabled"] = _enabled_value(payload.get("enabled"))
    elif "status" in payload:
        result["enabled"] = 1 if payload.get("status") == "已启用" else 0
    elif not partial:
        result["enabled"] = 1

    return result


def _enabled_param(value: Any) -> int | None:
    return None if value in (None, "") else _enabled_value(value)


def _enabled_value(value: Any) -> int:
    return 1 if int(value or 0) else 0


def _with_aliases(record: dict[str, Any]) -> dict[str, Any]:
    enabled = _enabled_value(record.get("enabled", 1))
    record["enabled"] = enabled
    record["desc"] = record.get("description") or ""
    record["status"] = "已启用" if enabled else "已停用"
    return record


dimension_repository = DimensionRepository()
