from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
import pymysql

from src.config import get_settings
from src.services.db_base import db_pool


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    return int(payload["sub"])


class UserRepository:
    def find_by_account(self, account: str) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM `user` WHERE account = %(account)s AND status = 1",
                        {"account": account},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 用户读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def find_by_id(self, user_id: int) -> dict[str, Any] | None:
        try:
            conn = db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM `user` WHERE id = %(id)s AND status = 1",
                        {"id": user_id},
                    )
                    row = cursor.fetchone()
            finally:
                conn.close()
        except pymysql.err.DatabaseError as exc:
            raise RuntimeError(f"MySQL 用户读取失败: {exc}") from exc
        return dict(row) if row is not None else None

    def update_by_id(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"name", "company", "phone", "email"}
        payload = {key: value for key, value in updates.items() if key in allowed}
        if payload:
            assignments = ", ".join(f"{key} = %({key})s" for key in payload)
            payload["id"] = user_id
            try:
                conn = db_pool.get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"UPDATE `user` SET {assignments} WHERE id = %(id)s",
                            payload,
                        )
                    conn.commit()
                finally:
                    conn.close()
            except pymysql.err.DatabaseError as exc:
                raise RuntimeError(f"MySQL 用户更新失败: {exc}") from exc
        return self.find_by_id(user_id)


user_repository = UserRepository()
