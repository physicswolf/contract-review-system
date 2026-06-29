from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.adapters import user_to_frontend
from src.api.responses import error_response, flat_object
from src.services.auth_service import create_token, user_repository, verify_password


router = APIRouter()


@router.post("/login")
async def login(payload: dict[str, Any]) -> JSONResponse:
    account = str(payload.get("account") or "").strip()
    password = str(payload.get("password") or "")
    if not account or not password:
        return error_response(422, "INVALID_LOGIN_PAYLOAD", "请输入账号和密码")

    try:
        user = user_repository.find_by_account(account)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "登录失败，请稍后重试")

    if user is None or not verify_password(password, str(user.get("password") or "")):
        return error_response(401, "INVALID_CREDENTIALS", "账号或密码错误")

    return flat_object({"token": create_token(int(user["id"])), "user": user_to_frontend(user)})


@router.get("/profile")
async def get_profile(request: Request) -> JSONResponse:
    try:
        user = user_repository.find_by_id(int(request.state.user_id))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "用户信息读取失败")

    if user is None:
        return error_response(404, "USER_NOT_FOUND", "用户不存在")
    return flat_object(user_to_frontend(user))


@router.put("/profile")
async def update_profile(request: Request, payload: dict[str, Any]) -> JSONResponse:
    try:
        user = user_repository.update_by_id(int(request.state.user_id), payload)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "用户信息更新失败")

    if user is None:
        return error_response(404, "USER_NOT_FOUND", "用户不存在")
    return flat_object(user_to_frontend(user))
