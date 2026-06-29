from __future__ import annotations

import pymysql
from pymysql.cursors import DictCursor

from src.config import Settings, get_settings


class DatabasePool:
    def get_connection(self, settings: Settings | None = None) -> pymysql.Connection:
        settings = settings or get_settings()
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

    def get_server_connection(self, settings: Settings | None = None) -> pymysql.Connection:
        settings = settings or get_settings()
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )


db_pool = DatabasePool()
