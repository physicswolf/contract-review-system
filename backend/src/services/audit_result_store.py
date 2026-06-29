from __future__ import annotations

from typing import Any

import pymysql

from src.services.db_base import db_pool


class AuditResultStore:
    def create_task(self, contract_id: int, stance: str, contract_type_id: int | None = None) -> int:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_task (contract_id, contract_type_id, stance, status)
                        VALUES (%(contract_id)s, %(contract_type_id)s, %(stance)s, 'running')
                        """,
                        {
                            "contract_id": contract_id,
                            "contract_type_id": contract_type_id,
                            "stance": stance,
                        },
                    )
                    task_id = int(cursor.lastrowid)
                conn.commit()
                return task_id
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核任务创建失败: {exc}") from exc

    def insert_results(self, task_id: int, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    for item in items:
                        cursor.execute(
                            """
                            INSERT INTO audit_result_item (
                                task_id, dim_id, dim_name, audit_point_id, title,
                                risk_level, risk_summary, risk_analysis,
                                modify_example, clause_name, hit_text, sort_order
                            )
                            VALUES (
                                %(task_id)s, %(dim_id)s, %(dim_name)s, %(audit_point_id)s,
                                %(title)s, %(risk_level)s, %(risk_summary)s,
                                %(risk_analysis)s, %(modify_example)s,
                                %(clause_name)s, %(hit_text)s, %(sort_order)s
                            )
                            """,
                            {"task_id": task_id, **item},
                        )
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核结果写入失败: {exc}") from exc

    def insert_stats(self, task_id: int, stats: list[dict[str, Any]]) -> None:
        if not stats:
            return
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    for stat in stats:
                        cursor.execute(
                            """
                            INSERT INTO audit_dimension_stat (
                                task_id, dim_id, dim_name, total_count, major_count, general_count
                            )
                            VALUES (
                                %(task_id)s, %(dim_id)s, %(dim_name)s,
                                %(total_count)s, %(major_count)s, %(general_count)s
                            )
                            ON DUPLICATE KEY UPDATE
                                total_count = VALUES(total_count),
                                major_count = VALUES(major_count),
                                general_count = VALUES(general_count)
                            """,
                            {"task_id": task_id, **stat},
                        )
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核统计写入失败: {exc}") from exc

    def complete_task(
        self,
        task_id: int,
        *,
        total: int,
        major: int,
        general: int,
        status: str = "succeeded",
    ) -> None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE audit_task
                           SET status = %(status)s,
                               total_risk_count = %(total)s,
                               major_risk_count = %(major)s,
                               general_risk_count = %(general)s
                         WHERE id = %(id)s
                        """,
                        {
                            "id": task_id,
                            "status": status,
                            "total": total,
                            "major": major,
                            "general": general,
                        },
                    )
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核任务更新失败: {exc}") from exc

    def get_latest_task_by_contract(self, contract_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT *
                          FROM audit_task
                         WHERE contract_id = %(contract_id)s
                         ORDER BY id DESC
                         LIMIT 1
                        """,
                        {"contract_id": contract_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核任务读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def get_results_by_task(self, task_id: int) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT *
                          FROM audit_result_item
                         WHERE task_id = %(task_id)s AND display = 1
                         ORDER BY sort_order ASC, id ASC
                        """,
                        {"task_id": task_id},
                    )
                    return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核结果读取失败: {exc}") from exc

    def get_stats_by_task(self, task_id: int) -> list[dict[str, Any]]:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT *
                          FROM audit_dimension_stat
                         WHERE task_id = %(task_id)s
                         ORDER BY dim_id ASC
                        """,
                        {"task_id": task_id},
                    )
                    return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 审核统计读取失败: {exc}") from exc


audit_result_store = AuditResultStore()
