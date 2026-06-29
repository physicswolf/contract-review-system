from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


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
