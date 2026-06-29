from __future__ import annotations

from fastapi import APIRouter

from src.schemas import HealthData


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return HealthData(version="0.2.0").model_dump()
