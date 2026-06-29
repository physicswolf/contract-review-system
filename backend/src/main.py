from __future__ import annotations

from fastapi import FastAPI

from src.api.audit_points import router as audit_points_router
from src.api.auth import router as auth_router
from src.api.contracts import router as contracts_router
from src.api.contract_types import router as contract_types_router
from src.api.dimensions import router as dimensions_router
from src.api.documents import router as documents_router
from src.api.files import router as files_router
from src.api.health import router as health_router
from src.api.internal import router as internal_router
from src.api.points import router as points_router
from src.api.review import router as review_router
from src.config import get_settings
from src.exception_handlers import register_exception_handlers
from src.lifecycle import app_lifespan
from src.middleware import register_middlewares


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI智契合同审核 API",
        version="0.2.0",
        lifespan=app_lifespan,
    )
    register_middlewares(app)
    register_exception_handlers(app)
    app.include_router(health_router, prefix=settings.api_prefix, tags=["系统"])
    app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["认证"])
    app.include_router(files_router, prefix=f"{settings.api_prefix}/files", tags=["文件服务"])
    app.include_router(
        documents_router,
        prefix=f"{settings.api_prefix}/documents",
        tags=["文档结构"],
    )
    app.include_router(
        contracts_router,
        prefix=f"{settings.api_prefix}/contracts",
        tags=["合同管理"],
    )
    app.include_router(
        review_router,
        prefix=f"{settings.api_prefix}/review",
        tags=["审核配置"],
    )
    app.include_router(points_router, prefix=f"{settings.api_prefix}/points", tags=["审查点"])
    app.include_router(
        audit_points_router,
        prefix=f"{settings.api_prefix}/audit-points",
        tags=["审查点(tmp兼容)"],
    )
    app.include_router(dimensions_router, prefix=f"{settings.api_prefix}/dimensions", tags=["审查维度"])
    app.include_router(
        contract_types_router,
        prefix=f"{settings.api_prefix}/contract-types",
        tags=["合同类型"],
    )
    app.include_router(internal_router, prefix=f"{settings.api_prefix}/internal", tags=["内部接口"])
    return app


app = create_app()
