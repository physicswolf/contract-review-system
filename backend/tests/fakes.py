from __future__ import annotations

from typing import Any

from src.services.contract_store import ContractRepository


class InMemoryContractRepository(ContractRepository):
    def __init__(self) -> None:
        self._records: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def initialize(self) -> None:
        return None

    def insert(self, record: dict[str, Any]) -> int:
        payload = _record_payload(record)
        contract_id = self._next_id
        self._next_id += 1
        payload["id"] = contract_id
        self._records[contract_id] = payload
        return contract_id

    def upsert_by_file_id(self, record: dict[str, Any]) -> int:
        payload = _record_payload(record)
        for contract_id, existing in self._records.items():
            if existing["file_id"] == payload["file_id"]:
                payload["id"] = contract_id
                self._records[contract_id] = payload
                return contract_id
        return self.insert(payload)

    def find_all(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        records = [
            dict(record)
            for record in self._records.values()
            if _matches(record, filters or {})
        ]
        return sorted(records, key=lambda record: record["review_time"], reverse=True)

    def find_by_id(self, contract_id: int) -> dict[str, Any] | None:
        record = self._records.get(contract_id)
        return dict(record) if record is not None else None

    def find_by_file_id(self, file_id: str) -> dict[str, Any] | None:
        for record in self._records.values():
            if record["file_id"] == file_id:
                return dict(record)
        return None

    def update_by_id(self, contract_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        record = self._records.get(contract_id)
        if record is None:
            return None
        for field in (
            "contract_name",
            "party_a",
            "party_b",
            "contract_type",
            "risk",
            "risk_count",
            "risk_level",
            "updated_at",
        ):
            if field in updates and updates[field] is not None:
                record[field] = str(updates[field])
        return dict(record)

    def update_risk_cache(
        self,
        contract_id: int,
        *,
        risk: str,
        risk_count: int,
        risk_level: str,
    ) -> None:
        record = self._records.get(contract_id)
        if record is not None:
            record["risk"] = risk
            record["risk_count"] = risk_count
            record["risk_level"] = risk_level

    def delete_by_id(self, contract_id: int) -> bool:
        return self._records.pop(contract_id, None) is not None

    def count(self, filters: dict[str, str] | None = None) -> int:
        return len(self.find_all(filters))


def _record_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
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


def _matches(record: dict[str, Any], filters: dict[str, str]) -> bool:
    return (
        _field_matches(record, filters, "contract_name")
        and _field_matches(record, filters, "party_a")
        and _field_matches(record, filters, "party_b")
        and _field_matches(record, filters, "contract_type")
    )


def _field_matches(
    record: dict[str, Any],
    filters: dict[str, str],
    field: str,
) -> bool:
    value = str(filters.get(field) or "").strip()
    return not value or value in str(record[field])
