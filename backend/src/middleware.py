from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.services.auth_service import decode_token


AUTH_WHITELIST = {
    "/api/health",
    "/api/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def jwt_auth_middleware(request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in AUTH_WHITELIST:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "未登录"})

        try:
            request.state.user_id = decode_token(auth_header[7:])
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

        return await call_next(request)

    @app.middleware("http")
    async def upload_size_guard(request: Request, call_next):
        settings = get_settings()
        upload_paths = {
            "/api/files/upload",
            f"{settings.api_prefix}/files/upload",
        }
        if request.method == "POST" and request.url.path in upload_paths:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > settings.max_upload_size_bytes + 1024:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "文件超过大小限制"},
                )

        response = await call_next(request)
        return response
