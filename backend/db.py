import json
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

_pool_cfg = dict(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)


def get_conn():
    return pymysql.connect(**_pool_cfg)


def ok(data=None):
    return {"code": 0, "msg": "ok", "data": data}


def err(code, msg, http=400):
    return {"code": code, "msg": msg}, http


def _parse_json_fields(row, fields):
    if row is None:
        return row
    for f in fields:
        v = row.get(f)
        if isinstance(v, str):
            try:
                row[f] = json.loads(v)
            except Exception:
                pass
    return row
