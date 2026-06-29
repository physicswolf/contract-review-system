from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ErrorInfo(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T | None = None
    message: str = ""


class ApiErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorInfo


class FileMeta(BaseModel):
    id: str
    original_name: str
    extension: str
    content_type: str
    size: int
    uploaded_at: str


class TaskErrorInfo(BaseModel):
    code: str
    message: str


class TaskMeta(BaseModel):
    id: str
    file_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    stage: str
    created_at: str
    updated_at: str
    error: TaskErrorInfo | None = None
    parsing_dir: str | None = None
    document_json_path: str | None = None


class HealthData(BaseModel):
    status: Literal["ok"] = "ok"
    version: str = "0.1.0"


class UploadData(BaseModel):
    file: FileMeta
    task: TaskMeta


class TaskData(BaseModel):
    task: TaskMeta


class FileData(BaseModel):
    file: FileMeta


class TaskStatusSuccess(BaseModel):
    success: Literal[True] = True
    task: TaskMeta


class UploadSuccess(BaseModel):
    success: Literal[True] = True
    file: FileMeta
    task: TaskMeta
    next_step: str = "processing"


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorInfo


class HealthResponse(BaseModel):
    success: Literal[True] = True
    status: Literal["ok"] = "ok"
    version: str = "0.1.0"


class DocumentInfo(BaseModel):
    file_id: str
    schema_name: str
    origin: dict[str, Any]
    has_structure: bool
    chapter_count: int
    warning_count: int


class DocumentInfoResponse(BaseModel):
    success: Literal[True] = True
    document: DocumentInfo


class DocumentData(BaseModel):
    document: DocumentInfo


class StructureMeta(BaseModel):
    schema_name: str
    file_id: str


class StructureData(BaseModel):
    meta: StructureMeta
    structure: dict[str, Any]


class StructureResponse(BaseModel):
    success: Literal[True] = True
    meta: StructureMeta
    structure: dict[str, Any]


class StructureUpdateRequest(BaseModel):
    structure: dict[str, Any]


class StructureUpdateResponse(BaseModel):
    success: Literal[True] = True
    message: str = "结构已保存"


class ContractRecord(BaseModel):
    id: int
    file_id: str
    contract_name: str
    party_a: str
    party_b: str
    contract_type: str
    review_time: str
    created_at: str


class ContractDetailRecord(ContractRecord):
    detail_url: str | None = None


class ContractFilterParams(BaseModel):
    contract_name: str = ""
    party_a: str = ""
    party_b: str = ""
    contract_type: str = ""


class ContractCreateRequest(BaseModel):
    file_id: str = Field(..., description="关联的解析文件 ID")
    contract_name: str = Field(default="", description="合同名称")
    party_a: str = Field(default="", description="甲方")
    party_b: str = Field(default="", description="乙方")
    contract_type: str = Field(default="未分类", description="合同类型")
    review_time: str = Field(..., description="审核时间 ISO8601")


class ContractUpdateRequest(BaseModel):
    contract_name: str | None = Field(default=None, description="合同名称")
    party_a: str | None = Field(default=None, description="甲方")
    party_b: str | None = Field(default=None, description="乙方")
    contract_type: str | None = Field(default=None, description="合同类型")


class ContractListData(BaseModel):
    contracts: list[ContractRecord]
    total: int


class ContractDetailData(BaseModel):
    contract: ContractDetailRecord


class ContractModifyData(BaseModel):
    contract: ContractRecord


class ContractListResponse(BaseModel):
    success: Literal[True] = True
    contracts: list[ContractRecord]
    total: int


class ContractDetailResponse(BaseModel):
    success: Literal[True] = True
    contract: ContractDetailRecord


class ContractDeleteResponse(BaseModel):
    success: Literal[True] = True
    message: str = "合同及相关文件已删除"
