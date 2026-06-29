from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
import pymysql

from src.services.contract_store import get_contract_repository
from src.services.db_base import db_pool
from src.services.document_parser import start_document_converter_warmup


MIGRATIONS_DIR = Path(__file__).resolve().parent / "db" / "migrations"


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_contract_repository()
    run_migrations()
    start_document_converter_warmup()
    yield


def run_migrations() -> None:
    if not MIGRATIONS_DIR.exists():
        return

    conn = db_pool.get_connection()
    try:
        _ensure_migration_table(conn)
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if _migration_applied(conn, sql_file.name):
                continue
            sql = sql_file.read_text(encoding="utf-8")
            with conn.cursor() as cursor:
                for statement in _split_sql(sql):
                    try:
                        cursor.execute(statement)
                    except pymysql.err.OperationalError as exc:
                        if exc.args[0] not in (1050, 1060, 1061):
                            raise
                cursor.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%(filename)s)",
                    {"filename": sql_file.name},
                )
            conn.commit()
    finally:
        conn.close()


def _ensure_migration_table(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) NOT NULL,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (filename)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
    conn.commit()


def _migration_applied(conn: pymysql.connections.Connection, filename: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT filename FROM schema_migrations WHERE filename = %(filename)s",
            {"filename": filename},
        )
        return cursor.fetchone() is not None


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    escaped = False

    for char in sql:
        current.append(char)
        if in_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_quote:
                in_quote = None
        elif char in {"'", '"'}:
            in_quote = char
        elif char == ";":
            statement = _clean_statement("".join(current).strip().rstrip(";").strip())
            if statement:
                statements.append(statement)
            current = []

    tail = _clean_statement("".join(current).strip())
    if tail:
        statements.append(tail)
    return statements


def _clean_statement(statement: str) -> str:
    lines = []
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
