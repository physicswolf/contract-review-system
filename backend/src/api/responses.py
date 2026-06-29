from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

ERR_PARAM = 40001
ERR_NOTFOUND = 40401
ERR_CONFLICT = 40901
ERR_SERVER = 50001


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": message},
    )


def flat_list(items: list[dict[str, Any]], total: int, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"items": items, "total": total})


def flat_object(obj: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=obj)


def ok_deleted() -> JSONResponse:
    return JSONResponse(status_code=200, content={"ok": True})


def tmp_ok(data: Any | None = None, status_code: int = 200) -> JSONResponse:
    content: dict[str, Any] = {"code": 0, "msg": "ok"}
    if data is not None:
        content["data"] = data
    return JSONResponse(status_code=status_code, content=content)


def tmp_error(status_code: int, code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "msg": message})
