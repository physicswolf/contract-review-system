from __future__ import annotations

from typing import Any

import pymysql
import pytest

from src.config import Settings
from src.services.contract_store import (
    MysqlContractRepository,
    get_contract_repository,
)


def test_mysql_repository_crud_with_pymysql(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMysql()
    monkeypatch.setattr("src.services.contract_store.pymysql.connect", fake.connect)
    repo = MysqlContractRepository(mysql_settings())
    repo.initialize()

    contract_id = repo.upsert_by_file_id(sample_record("file-001", "采购合同"))
    assert contract_id == 1
    assert repo.count() == 1
    assert repo.find_all({"contract_type": "采购"})[0]["file_id"] == "file-001"

    repo.upsert_by_file_id(
        sample_record("file-001", "采购合同", contract_name="修改后的合同")
    )
    assert repo.count() == 1
    assert repo.find_by_id(contract_id)["contract_name"] == "修改后的合同"

    updated = repo.update_by_id(
        contract_id,
        {"party_b": "新的乙方公司", "updated_at": "2026-06-26T12:00:00+08:00"},
    )
    assert updated["party_b"] == "新的乙方公司"

    assert repo.delete_by_id(contract_id) is True
    assert repo.count() == 0
    assert fake.connections[0]["database"] is None
    assert fake.connections[-1]["database"] == "aizhiqi_test"
    assert any(
        "ON DUPLICATE KEY UPDATE" in sql for sql in fake.executed_sql
    )
    assert any("CONCAT('%%'" in sql for sql in fake.executed_sql)


def test_contract_repository_factory_returns_mysql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeMysql()
    monkeypatch.setattr("src.services.contract_store.pymysql.connect", fake.connect)

    repo = get_contract_repository(mysql_settings())

    assert isinstance(repo, MysqlContractRepository)
    assert fake.connections[0]["host"] == "127.0.0.1"
    assert fake.connections[0]["user"] == "root"


def test_mysql_initialize_reports_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_connect(**kwargs: Any) -> None:
        raise pymysql.err.OperationalError(2003, "cannot connect")

    monkeypatch.setattr("src.services.contract_store.pymysql.connect", fail_connect)
    repo = MysqlContractRepository(mysql_settings())

    with pytest.raises(RuntimeError, match="MySQL 连接失败"):
        repo.initialize()


class FakeMysql:
    def __init__(self) -> None:
        self.connections: list[dict[str, Any]] = []
        self.contracts: dict[str, dict[str, Any]] = {}
        self.next_id = 1
        self.executed_sql: list[str] = []

    def connect(self, **kwargs: Any) -> "FakeConnection":
        kwargs.setdefault("database", None)
        self.connections.append(kwargs)
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, fake: FakeMysql) -> None:
        self.fake = fake
        self.closed = False
        self.committed = False

    def cursor(self) -> "FakeCursor":
        return FakeCursor(self.fake)

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


class FakeCursor:
    def __init__(self, fake: FakeMysql) -> None:
        self.fake = fake
        self.rowcount = 0
        self.lastrowid = 0
        self._rows: list[dict[str, Any]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        self.fake.executed_sql.append(sql)
        normalized = " ".join(sql.split()).lower()
        payload = params or {}

        if (
            normalized.startswith("create database")
            or normalized.startswith("create table")
            or normalized.startswith("alter table")
        ):
            self._rows = []
            self.rowcount = 0
            return

        if normalized.startswith("insert into contracts"):
            self._upsert_contract(payload, "on duplicate key update" in normalized)
            return

        if normalized.startswith("select id from contracts where file_id"):
            record = self.fake.contracts.get(str(payload["file_id"]))
            self._rows = [{"id": record["id"]}] if record else []
            return

        if normalized.startswith("select count(*)"):
            self._rows = [{"total": len(self._filtered_records(payload))}]
            return

        if normalized.startswith("select id,") and "where id =" in normalized:
            contract_id = int(payload["id"])
            self._rows = [
                record
                for record in self.fake.contracts.values()
                if int(record["id"]) == contract_id
            ]
            return

        if normalized.startswith("select id,"):
            self._rows = sorted(
                self._filtered_records(payload),
                key=lambda record: record["review_time"],
                reverse=True,
            )
            return

        if normalized.startswith("update contracts set"):
            contract_id = int(payload["id"])
            for record in self.fake.contracts.values():
                if int(record["id"]) == contract_id:
                    for key, value in payload.items():
                        if key != "id":
                            record[key] = value
                    self.rowcount = 1
                    return
            self.rowcount = 0
            return

        if normalized.startswith("delete from contracts"):
            contract_id = int(payload["id"])
            for file_id, record in list(self.fake.contracts.items()):
                if int(record["id"]) == contract_id:
                    self.fake.contracts.pop(file_id)
                    self.rowcount = 1
                    return
            self.rowcount = 0
            return

        raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def _upsert_contract(self, payload: dict[str, Any], allow_update: bool) -> None:
        file_id = str(payload["file_id"])
        if file_id in self.fake.contracts:
            if not allow_update:
                raise AssertionError("duplicate insert without upsert")
            self.fake.contracts[file_id].update(_contract_payload(payload))
            self.rowcount = 2
            self.lastrowid = int(self.fake.contracts[file_id]["id"])
            return

        record = _contract_payload(payload)
        record["id"] = self.fake.next_id
        self.fake.next_id += 1
        self.fake.contracts[file_id] = record
        self.rowcount = 1
        self.lastrowid = int(record["id"])

    def _filtered_records(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            record
            for record in self.fake.contracts.values()
            if _matches(record, "contract_name", filters)
            and _matches(record, "party_a", filters)
            and _matches(record, "party_b", filters)
            and _matches(record, "contract_type", filters)
        ]


def _contract_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_id": payload["file_id"],
        "contract_name": payload["contract_name"],
        "party_a": payload["party_a"],
        "party_b": payload["party_b"],
        "contract_type": payload["contract_type"],
        "review_time": payload["review_time"],
        "risk": payload.get("risk", "未审核"),
        "risk_count": payload.get("risk_count", 0),
        "risk_level": payload.get("risk_level", "green"),
        "created_at": payload["created_at"],
        "updated_at": payload["updated_at"],
    }


def _matches(
    record: dict[str, Any],
    field: str,
    filters: dict[str, Any],
) -> bool:
    value = str(filters.get(field) or "")
    return not value or value in str(record[field])


def sample_record(
    file_id: str,
    contract_type: str,
    *,
    contract_name: str = "测试合同",
) -> dict[str, str]:
    return {
        "file_id": file_id,
        "contract_name": contract_name,
        "party_a": "甲方公司",
        "party_b": "乙方公司",
        "contract_type": contract_type,
        "review_time": "2026-06-26T10:00:00+08:00",
        "created_at": "2026-06-26T10:00:00+08:00",
        "updated_at": "2026-06-26T10:00:00+08:00",
    }


def mysql_settings() -> Settings:
    return Settings(
        mysql_host="127.0.0.1",
        mysql_port=3306,
        mysql_user="root",
        mysql_password="secret",
        mysql_database="aizhiqi_test",
    )
