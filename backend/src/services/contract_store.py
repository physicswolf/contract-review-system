from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pymysql

from src.config import Settings, get_settings
from src.services.db_base import db_pool


CONTRACT_FIELDS = (
    "id",
    "file_id",
    "contract_name",
    "party_a",
    "party_b",
    "contract_type",
    "review_time",
    "risk",
    "risk_count",
    "risk_level",
    "created_at",
    "updated_at",
)


class ContractRepository(ABC):
    """合同存储抽象接口。"""

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def insert(self, record: dict[str, Any]) -> int:
        pass

    @abstractmethod
    def upsert_by_file_id(self, record: dict[str, Any]) -> int:
        pass

    @abstractmethod
    def find_all(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def find_by_id(self, contract_id: int) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def find_by_file_id(self, file_id: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def update_by_id(self, contract_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def update_risk_cache(
        self,
        contract_id: int,
        *,
        risk: str,
        risk_count: int,
        risk_level: str,
    ) -> None:
        pass

    @abstractmethod
    def delete_by_id(self, contract_id: int) -> bool:
        pass

    @abstractmethod
    def count(self, filters: dict[str, str] | None = None) -> int:
        pass


class MysqlContractRepository(ContractRepository):
    def __init__(self, settings: Settings):
        self._settings = settings

    def initialize(self) -> None:
        database = _mysql_identifier(self._settings.mysql_database)
        try:
            conn = self._get_server_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS {database} "
                        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                conn.commit()
            finally:
                conn.close()

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS contracts (
                            id              INT AUTO_INCREMENT PRIMARY KEY,
                            file_id         VARCHAR(64)  NOT NULL,
                            contract_name   VARCHAR(256) NOT NULL DEFAULT '',
                            party_a         VARCHAR(256) NOT NULL DEFAULT '',
                            party_b         VARCHAR(256) NOT NULL DEFAULT '',
                            contract_type   VARCHAR(64)  NOT NULL DEFAULT '未分类',
                            review_time     VARCHAR(32)  NOT NULL,
                            risk            VARCHAR(20)  NOT NULL DEFAULT '未审核',
                            risk_count      INT          NOT NULL DEFAULT 0,
                            risk_level      VARCHAR(20)  NOT NULL DEFAULT 'green',
                            created_at      VARCHAR(32)  NOT NULL,
                            updated_at      VARCHAR(32)  NOT NULL,
                            UNIQUE KEY uk_file_id (file_id),
                            INDEX idx_review_time (review_time)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                          COLLATE=utf8mb4_unicode_ci
                        """
                    )
                    _ensure_column(cursor, "contracts", "risk", "VARCHAR(20) NOT NULL DEFAULT '未审核'")
                    _ensure_column(cursor, "contracts", "risk_count", "INT NOT NULL DEFAULT 0")
                    _ensure_column(cursor, "contracts", "risk_level", "VARCHAR(20) NOT NULL DEFAULT 'green'")
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.OperationalError as exc:
            raise RuntimeError(
                f"MySQL 连接失败 ({self._settings.mysql_host}:{self._settings.mysql_port})，"
                "请检查数据库是否可访问"
            ) from exc
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 初始化失败: {exc}") from exc

    def insert(self, record: dict[str, Any]) -> int:
        payload = _record_payload(record)
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO contracts (
                            file_id,
                            contract_name,
                            party_a,
                            party_b,
                            contract_type,
                            review_time,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            %(file_id)s,
                            %(contract_name)s,
                            %(party_a)s,
                            %(party_b)s,
                            %(contract_type)s,
                            %(review_time)s,
                            %(created_at)s,
                            %(updated_at)s
                        )
                        """,
                        payload,
                    )
                    contract_id = int(cursor.lastrowid)
                conn.commit()
                return contract_id
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同记录插入失败: {exc}") from exc

    def upsert_by_file_id(self, record: dict[str, Any]) -> int:
        payload = _record_payload(record)
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO contracts (
                            file_id,
                            contract_name,
                            party_a,
                            party_b,
                            contract_type,
                            review_time,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            %(file_id)s,
                            %(contract_name)s,
                            %(party_a)s,
                            %(party_b)s,
                            %(contract_type)s,
                            %(review_time)s,
                            %(created_at)s,
                            %(updated_at)s
                        )
                        ON DUPLICATE KEY UPDATE
                            contract_name = VALUES(contract_name),
                            party_a       = VALUES(party_a),
                            party_b       = VALUES(party_b),
                            contract_type = VALUES(contract_type),
                            review_time   = VALUES(review_time),
                            updated_at    = VALUES(updated_at)
                        """,
                        payload,
                    )
                conn.commit()

                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM contracts WHERE file_id = %(file_id)s",
                        {"file_id": payload["file_id"]},
                    )
                    row = cursor.fetchone()
                return int(row["id"])
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同记录保存失败: {exc}") from exc

    def find_all(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        payload = _filter_payload(filters)
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id,
                               file_id,
                               contract_name,
                               party_a,
                               party_b,
                               contract_type,
                               review_time,
                               risk,
                               risk_count,
                               risk_level,
                               created_at,
                               updated_at
                          FROM contracts
                         WHERE (%(contract_name)s = '' OR contract_name LIKE CONCAT('%%', %(contract_name)s, '%%'))
                           AND (%(party_a)s = '' OR party_a LIKE CONCAT('%%', %(party_a)s, '%%'))
                           AND (%(party_b)s = '' OR party_b LIKE CONCAT('%%', %(party_b)s, '%%'))
                           AND (%(contract_type)s = '' OR contract_type LIKE CONCAT('%%', %(contract_type)s, '%%'))
                         ORDER BY review_time DESC
                        """,
                        payload,
                    )
                    rows = cursor.fetchall()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同列表读取失败: {exc}") from exc
        return [_mysql_row_to_dict(row) for row in rows]

    def find_by_id(self, contract_id: int) -> dict[str, Any] | None:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id,
                               file_id,
                               contract_name,
                               party_a,
                               party_b,
                               contract_type,
                               review_time,
                               risk,
                               risk_count,
                               risk_level,
                               created_at,
                               updated_at
                          FROM contracts
                         WHERE id = %(id)s
                        """,
                        {"id": contract_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同详情读取失败: {exc}") from exc
        return _mysql_row_to_dict(row) if row is not None else None

    def find_by_file_id(self, file_id: str) -> dict[str, Any] | None:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id,
                               file_id,
                               contract_name,
                               party_a,
                               party_b,
                               contract_type,
                               review_time,
                               risk,
                               risk_count,
                               risk_level,
                               created_at,
                               updated_at
                          FROM contracts
                         WHERE file_id = %(file_id)s
                        """,
                        {"file_id": file_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同详情读取失败: {exc}") from exc
        return _mysql_row_to_dict(row) if row is not None else None

    def update_by_id(self, contract_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        allowed_fields = (
            "contract_name",
            "party_a",
            "party_b",
            "contract_type",
            "risk",
            "risk_count",
            "risk_level",
            "updated_at",
        )
        payload = {
            key: str(value)
            for key, value in updates.items()
            if key in allowed_fields and value is not None
        }
        if not payload:
            return self.find_by_id(contract_id)

        assignments = ", ".join(f"{field} = %({field})s" for field in payload)
        payload["id"] = str(contract_id)

        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE contracts SET {assignments} WHERE id = %(id)s",
                        payload,
                    )
                conn.commit()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同更新失败: {exc}") from exc
        return self.find_by_id(contract_id)

    def update_risk_cache(
        self,
        contract_id: int,
        *,
        risk: str,
        risk_count: int,
        risk_level: str,
    ) -> None:
        self.update_by_id(
            contract_id,
            {
                "risk": risk,
                "risk_count": risk_count,
                "risk_level": risk_level,
            },
        )

    def delete_by_id(self, contract_id: int) -> bool:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM contracts WHERE id = %(id)s",
                        {"id": contract_id},
                    )
                    deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同删除失败: {exc}") from exc

    def count(self, filters: dict[str, str] | None = None) -> int:
        payload = _filter_payload(filters)
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS total
                          FROM contracts
                         WHERE (%(contract_name)s = '' OR contract_name LIKE CONCAT('%%', %(contract_name)s, '%%'))
                           AND (%(party_a)s = '' OR party_a LIKE CONCAT('%%', %(party_a)s, '%%'))
                           AND (%(party_b)s = '' OR party_b LIKE CONCAT('%%', %(party_b)s, '%%'))
                           AND (%(contract_type)s = '' OR contract_type LIKE CONCAT('%%', %(contract_type)s, '%%'))
                        """,
                        payload,
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 合同数量统计失败: {exc}") from exc
        return int(row["total"])

    def _get_server_connection(self) -> pymysql.Connection:
        return db_pool.get_server_connection(self._settings)

    def _get_connection(self) -> pymysql.Connection:
        return db_pool.get_connection(self._settings)


_repository: ContractRepository | None = None
_repository_settings_hash: int | None = None


def get_contract_repository(settings: Settings | None = None) -> ContractRepository:
    global _repository, _repository_settings_hash

    resolved = settings or get_settings()
    current_hash = _settings_hash(resolved)
    if _repository is None or _repository_settings_hash != current_hash:
        _repository = MysqlContractRepository(resolved)
        _repository.initialize()
        _repository_settings_hash = current_hash
    return _repository


def _settings_hash(settings: Settings) -> int:
    key = (
        settings.mysql_host,
        settings.mysql_port,
        settings.mysql_user,
        settings.mysql_password,
        settings.mysql_database,
    )
    return hash(key)


def _record_payload(record: dict[str, Any]) -> dict[str, str]:
    return {
        "file_id": str(record.get("file_id") or ""),
        "contract_name": str(record.get("contract_name") or ""),
        "party_a": str(record.get("party_a") or ""),
        "party_b": str(record.get("party_b") or ""),
        "contract_type": str(record.get("contract_type") or "未分类"),
        "review_time": str(record.get("review_time") or ""),
        "risk": str(record.get("risk") or "未审核"),
        "risk_count": int(record.get("risk_count") or 0),
        "risk_level": str(record.get("risk_level") or "green"),
        "created_at": str(record.get("created_at") or record.get("review_time") or ""),
        "updated_at": str(record.get("updated_at") or record.get("review_time") or ""),
    }


def _filter_payload(filters: dict[str, str] | None) -> dict[str, str]:
    filters = filters or {}
    return {
        "contract_name": filters.get("contract_name", "").strip(),
        "party_a": filters.get("party_a", "").strip(),
        "party_b": filters.get("party_b", "").strip(),
        "contract_type": filters.get("contract_type", "").strip(),
    }


def _mysql_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in CONTRACT_FIELDS}


def _mysql_identifier(name: str) -> str:
    if not name:
        raise RuntimeError("MySQL 数据库名不能为空")
    return f"`{name.replace('`', '``')}`"


def _ensure_column(cursor: Any, table: str, column: str, definition: str) -> None:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except pymysql.err.OperationalError as exc:
        if exc.args[0] != 1060:
            raise
