from __future__ import annotations

from typing import Any

import pymysql

from src.services.db_base import db_pool


class DimensionRepository:
    def find_all(self) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, `desc`, sort_order, status, created_at, updated_at
                          FROM dimension
                         ORDER BY sort_order ASC, id ASC
                        """
                    )
                    return [dict(row) for row in cursor.fetchall()]
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
                        "SELECT * FROM dimension WHERE id = %(id)s",
                        {"id": dimension_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM dimension WHERE name = %(name)s",
                        {"name": name},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def find_names(self) -> list[str]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT name
                          FROM dimension
                         WHERE status = '已启用'
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
                        SELECT name, `desc`
                          FROM dimension
                         WHERE status = '已启用'
                         ORDER BY sort_order ASC, id ASC
                        """
                    )
                    return [dict(row) for row in cursor.fetchall()]
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
                        INSERT INTO dimension (name, `desc`, sort_order, status)
                        VALUES (%(name)s, %(desc)s, %(sort_order)s, %(status)s)
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
        allowed = {"name", "desc", "sort_order", "status"}
        payload = {key: value for key, value in updates.items() if key in allowed}
        if not payload:
            return self.find_by_id(dimension_id)

        assignments = ", ".join(
            f"`{key}` = %({key})s" if key == "desc" else f"{key} = %({key})s"
            for key in payload
        )
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
                    if int(cursor.fetchone()["total"]) > 0:
                        raise ValueError("该维度下仍有关联审查点，不能删除")
                    cursor.execute(
                        "DELETE FROM dimension WHERE id = %(id)s",
                        {"id": dimension_id},
                    )
                    deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
            finally:
                conn.close()
        except ValueError:
            raise
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 维度删除失败: {exc}") from exc


def _payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(payload.get("name") or "").strip(),
        "desc": str(payload.get("desc") or ""),
        "sort_order": int(payload.get("sort_order") or 0),
        "status": str(payload.get("status") or "已启用"),
    }


dimension_repository = DimensionRepository()
