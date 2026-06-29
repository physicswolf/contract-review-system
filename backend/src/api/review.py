from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.responses import flat_list


router = APIRouter()

DEFAULT_PURPOSES = [
    {
        "id": 1,
        "name": "条款完整性",
        "description": "检查合同条款是否完整无遗漏",
    },
    {
        "id": 2,
        "name": "风险识别",
        "description": "识别合同中的潜在风险点",
    },
    {
        "id": 3,
        "name": "合规性检查",
        "description": "检查合同是否符合相关法规要求",
    },
    {
        "id": 4,
        "name": "权责对等",
        "description": "检查双方权利义务是否对等",
    },
]


@router.get("/purposes")
async def list_purposes() -> JSONResponse:
    """Return the default review purpose options."""
    return flat_list(DEFAULT_PURPOSES, len(DEFAULT_PURPOSES))
