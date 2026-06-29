from __future__ import annotations

import json
from typing import Any

import pymysql

from src.services.db_base import db_pool
from src.services.dimension_store import dimension_repository


class AuditPointRepository:
    def find_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        keyword = str(filters.get("keyword") or "").strip()
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ap.*,
                               d.name AS dim_name,
                               COALESCE(JSON_LENGTH(ap.risk_points), 0) AS risk_points_count
                          FROM audit_point ap
                          JOIN dimension d ON d.id = ap.dim_id
                         WHERE ap.deleted_at IS NULL
                           AND (%(keyword)s = '' OR ap.name LIKE CONCAT('%%', %(keyword)s, '%%'))
                         ORDER BY ap.sort_order ASC, ap.id ASC
                        """,
                        {"keyword": keyword},
                    )
                    return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点列表读取失败: {exc}") from exc

    def count(self, filters: dict[str, Any] | None = None) -> int:
        return len(self.find_all(filters))

    def find_by_id(self, point_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ap.*,
                               d.name AS dim_name,
                               COALESCE(JSON_LENGTH(ap.risk_points), 0) AS risk_points_count
                          FROM audit_point ap
                          JOIN dimension d ON d.id = ap.dim_id
                         WHERE ap.id = %(id)s AND ap.deleted_at IS NULL
                        """,
                        {"id": point_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审查点读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def insert(self, payload: dict[str, Any]) -> int:
        data = self._payload(payload)
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_point (
                            dim_id, name, category, `desc`, instruction,
                            risk_points, examples, default_result,
                            default_checked, status, sort_order
                        )
                        VALUES (
                            %(dim_id)s, %(name)s, %(category)s, %(desc)s, %(instruction)s,
                            %(risk_points)s, %(examples)s, %(default_result)s,
                            %(default_checked)s, %(status)s, %(sort_order)s
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

    def update_by_id(self, point_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        data = self._payload(updates, partial=True)
        if not data:
            return self.find_by_id(point_id)

        assignments = ", ".join(f"`{key}` = %({key})s" if key == "desc" else f"{key} = %({key})s" for key in data)
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

    def _payload(self, payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if "dim_id" in payload or "dimension" in payload or not partial:
            result["dim_id"] = _resolve_dim_id(payload)
        for key in ("name", "category", "desc", "instruction", "status"):
            if key in payload:
                result[key] = str(payload.get(key) or "")
            elif not partial:
                result[key] = "" if key != "status" else "已启用"
        if "default_checked" in payload:
            result["default_checked"] = 1 if payload.get("default_checked") else 0
        elif not partial:
            result["default_checked"] = 1
        if "sort_order" in payload:
            result["sort_order"] = int(payload.get("sort_order") or 0)
        elif not partial:
            result["sort_order"] = 0
        for key in ("risk_points", "examples", "default_result"):
            if key in payload:
                result[key] = _json_dump(payload.get(key), _fallback_json(key, payload))
            elif not partial:
                result[key] = _json_dump(_fallback_json(key, payload), [])
        return result


def _resolve_dim_id(payload: dict[str, Any]) -> int:
    dim_id = payload.get("dim_id")
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


def _fallback_json(key: str, payload: dict[str, Any]) -> Any:
    name = str(payload.get("name") or "审查点")
    desc = str(payload.get("desc") or "")
    if key == "risk_points":
        return [{
            "title": name,
            "clauseNote": "",
            "high": desc or "存在较高合同风险",
            "low": "存在一般合同风险",
        }]
    if key == "examples":
        return []
    return {
        "clause": "",
        "model": "",
        "overview": desc or f"{name}存在潜在风险，需要进一步核查。",
        "solution": "建议补充明确条款、责任边界和违约后果。",
    }


audit_point_repository = AuditPointRepository()
