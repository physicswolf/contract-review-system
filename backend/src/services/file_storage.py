from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

from fastapi import UploadFile

from src.config import Settings
from src.schemas import FileMeta


CHUNK_SIZE = 1024 * 1024
SIGNATURE_BUFFER_SIZE = 8192
SHANGHAI_TZ = timezone(timedelta(hours=8))

ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
}

ERROR_MESSAGES = {
    "EMPTY_FILE": "文件内容为空",
    "FILE_TOO_LARGE": "文件超过大小限制",
    "INVALID_FILENAME": "文件名异常",
    "UNSUPPORTED_FILE_TYPE": "仅支持 .docx、.pdf 文件",
    "FILE_SIGNATURE_MISMATCH": "文件内容与扩展名不匹配",
    "STORAGE_ERROR": "文件保存失败，请稍后重试",
}


@dataclass(frozen=True)
class StoredUpload:
    metadata: FileMeta
    path: Path
    metadata_path: Path


class UploadError(Exception):
    def __init__(self, code: str, message: str | None = None, status_code: int = 400):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "上传失败")
        self.status_code = status_code
        super().__init__(self.message)


def find_upload_metadata(file_id: str, settings: Settings) -> FileMeta | None:
    if not file_id:
        return None

    try:
        metadata_files = settings.upload_root.rglob("*.json")
        for metadata_path in metadata_files:
            if metadata_path.stem != file_id:
                continue
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            return FileMeta.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return None


async def save_upload(file: UploadFile, settings: Settings) -> StoredUpload:
    original_name = file.filename or ""
    extension = _validate_filename(original_name)
    content_type = _validate_content_type(extension, file.content_type)

    uploaded_at = datetime.now(SHANGHAI_TZ)
    file_id = str(uuid4())
    upload_dir = settings.upload_root / uploaded_at.strftime("%Y/%m/%d")
    final_path = upload_dir / f"{file_id}{extension}"
    temp_path = upload_dir / f"{file_id}{extension}.part"
    metadata_path = upload_dir / f"{file_id}.json"

    size = 0
    signature = bytearray()

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "wb") as output:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break

                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise UploadError("FILE_TOO_LARGE", status_code=413)

                if len(signature) < SIGNATURE_BUFFER_SIZE:
                    needed = SIGNATURE_BUFFER_SIZE - len(signature)
                    signature.extend(chunk[:needed])

                output.write(chunk)

        if size == 0:
            raise UploadError("EMPTY_FILE", status_code=400)

        if not _signature_matches(extension, bytes(signature), temp_path):
            raise UploadError("FILE_SIGNATURE_MISMATCH", status_code=415)

        temp_path.replace(final_path)
        metadata = FileMeta(
            id=file_id,
            original_name=original_name,
            extension=extension,
            content_type=content_type,
            size=size,
            uploaded_at=uploaded_at.isoformat(timespec="seconds"),
        )
        _write_metadata(metadata_path, metadata)
        return StoredUpload(metadata=metadata, path=final_path, metadata_path=metadata_path)
    except UploadError:
        _safe_unlink(temp_path)
        _safe_unlink(final_path)
        _safe_unlink(metadata_path)
        raise
    except OSError as exc:
        _safe_unlink(temp_path)
        _safe_unlink(final_path)
        _safe_unlink(metadata_path)
        raise UploadError("STORAGE_ERROR", status_code=500) from exc
    finally:
        try:
            file.file.close()
        except OSError:
            pass


def _validate_filename(filename: str) -> str:
    if not filename:
        raise UploadError("INVALID_FILENAME", status_code=400)

    if any(ord(char) < 32 or ord(char) == 127 for char in filename):
        raise UploadError("INVALID_FILENAME", status_code=400)

    if "/" in filename or "\\" in filename:
        raise UploadError("INVALID_FILENAME", status_code=400)

    if PurePosixPath(filename).is_absolute() or PureWindowsPath(filename).is_absolute():
        raise UploadError("INVALID_FILENAME", status_code=400)

    posix_parts = PurePosixPath(filename).parts
    windows_parts = PureWindowsPath(filename).parts
    if ".." in posix_parts or ".." in windows_parts:
        raise UploadError("INVALID_FILENAME", status_code=400)

    path = PurePosixPath(filename)
    extension = path.suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise UploadError("UNSUPPORTED_FILE_TYPE", status_code=415)

    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) > 1 and any(suffix in ALLOWED_TYPES for suffix in suffixes[:-1]):
        raise UploadError("INVALID_FILENAME", status_code=400)

    return extension


def _validate_content_type(extension: str, raw_content_type: str | None) -> str:
    content_type = (raw_content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_TYPES[extension]:
        raise UploadError("UNSUPPORTED_FILE_TYPE", status_code=415)
    return content_type


def _signature_matches(extension: str, signature: bytes, path: Path) -> bool:
    if extension == ".pdf":
        return signature.startswith(b"%PDF-")
    if extension == ".docx":
        return _is_docx_container(path)
    return False


def _is_docx_container(path: Path) -> bool:
    if not zipfile.is_zipfile(path):
        return False

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return False

    return "[Content_Types].xml" in names and any(
        name.startswith("word/") for name in names
    )


def _write_metadata(path: Path, metadata: FileMeta) -> None:
    payload = metadata.model_dump()
    with open(path, "w", encoding="utf-8") as output:
        output.write(json.dumps(payload, ensure_ascii=False, indent=2))


def delete_stored_upload(upload: StoredUpload) -> None:
    _safe_unlink(upload.path)
    _safe_unlink(upload.metadata_path)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
