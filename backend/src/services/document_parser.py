from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import Settings


SUPPORTED_EXTENSIONS = {".docx", ".pdf"}
PARSED_JSON_FILENAME = "document.json"
CONVERTED_PDF_FILENAME = "document.pdf"
CLEANED_DOCX_FILENAME = "document.no-header-footer.docx"
LIBREOFFICE_PDF_EXPORT_OPTIONS = {
    "ExportBookmarks": {"type": "boolean", "value": "false"},
    "InitialView": {"type": "long", "value": "0"},
}
_LOGGER = logging.getLogger(__name__)
_TORCHVISION_NMS_LIB: Any | None = None
_DOCUMENT_CONVERTER: Any | None = None
_DOCUMENT_CONVERTER_LOCK = threading.Lock()
_DOCUMENT_CONVERTER_WARMUP_STARTED = False

ERROR_MESSAGES = {
    "UNSUPPORTED_PARSE_TYPE": "仅支持 .docx、.pdf 文件解析",
    "UNSUPPORTED_DOCX_PARSER_ENGINE": "DOCX_PARSER_ENGINE 仅支持 docling、python-docx 或 pymupdf4llm",
    "UNSUPPORTED_PDF_PARSER_ENGINE": "PDF_PARSER_ENGINE 仅支持 docling 或 pymupdf4llm",
    "DOCUMENT_CONVERSION_ERROR": "Word 文件转换 PDF 失败，请检查 LibreOffice 环境",
    "DOCUMENT_PARSING_ERROR": "文档解析失败，请确认文件为纯文字版 PDF 或 DOCX",
}


@dataclass(frozen=True)
class ParsingArtifacts:
    directory: Path
    json_path: Path
    pdf_path: Path | None = None


class ParsingError(Exception):
    def __init__(self, code: str, message: str | None = None, status_code: int = 422):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "文档解析失败")
        self.status_code = status_code
        super().__init__(self.message)


def delete_parsing_artifacts(artifacts: "ParsingArtifacts") -> None:
    shutil.rmtree(artifacts.directory, ignore_errors=True)


def parse_uploaded_document(
    source_path: Path,
    file_id: str,
    extension: str,
    settings: Settings,
) -> ParsingArtifacts:
    extension = extension.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ParsingError("UNSUPPORTED_PARSE_TYPE", status_code=415)

    parsing_dir = settings.parsing_root / file_id
    json_path = parsing_dir / PARSED_JSON_FILENAME
    docx_parser_engine = (
        normalize_docx_parser_engine(settings.docx_parser_engine)
        if extension == ".docx"
        else "docling"
    )
    pdf_parser_engine = (
        normalize_pdf_parser_engine(settings.pdf_parser_engine)
        if extension == ".pdf"
        else "docling"
    )
    pdf_path = (
        parsing_dir / CONVERTED_PDF_FILENAME
        if extension == ".docx" and docx_parser_engine in {"docling", "pymupdf4llm"}
        else None
    )
    cleaned_docx_path = (
        parsing_dir / CLEANED_DOCX_FILENAME
        if extension == ".docx" and docx_parser_engine in {"docling", "pymupdf4llm"}
        else None
    )

    try:
        parsing_dir.mkdir(parents=True, exist_ok=True)
        conversion_input_path = source_path
        if extension == ".docx" and docx_parser_engine == "python-docx":
            try:
                json_data = convert_docx_to_python_docx_json_data(source_path, file_id)
            except Exception as exc:
                raise ParsingError("DOCUMENT_PARSING_ERROR", status_code=422) from exc
        else:
            if pdf_path is not None:
                try:
                    if cleaned_docx_path is None:
                        raise RuntimeError("cleaned DOCX path was not initialized")
                    conversion_input_path = remove_docx_headers_footers(
                        source_path,
                        cleaned_docx_path,
                    )
                    conversion_input_path = convert_docx_to_pdf(conversion_input_path, pdf_path)
                except Exception as exc:
                    raise ParsingError("DOCUMENT_CONVERSION_ERROR", status_code=500) from exc

            try:
                if extension == ".pdf" and pdf_parser_engine == "pymupdf4llm":
                    json_data = convert_pdf_to_pymupdf4llm_json_data(source_path, file_id)
                elif extension == ".docx" and docx_parser_engine == "pymupdf4llm":
                    json_data = convert_pdf_to_pymupdf4llm_json_data(
                        conversion_input_path,
                        file_id,
                    )
                else:
                    json_data = convert_to_json_data(conversion_input_path)
                    if extension == ".pdf":
                        json_data = add_docling_pdf_contract_structure(
                            json_data,
                            source_path,
                            file_id,
                        )
            except Exception as exc:
                raise ParsingError("DOCUMENT_PARSING_ERROR", status_code=422) from exc

        write_json_atomically(json_path, json_data)
        return ParsingArtifacts(directory=parsing_dir, json_path=json_path, pdf_path=pdf_path)
    except ParsingError:
        shutil.rmtree(parsing_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(parsing_dir, ignore_errors=True)
        raise ParsingError("DOCUMENT_PARSING_ERROR", status_code=500) from exc


def has_torchvision_nms_issue(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if "torchvision::nms" in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def patch_torchvision_nms_import_issue() -> None:
    global _TORCHVISION_NMS_LIB

    if _TORCHVISION_NMS_LIB is not None:
        return

    try:
        import torch

        lib = torch.library.Library("torchvision", "DEF")
        lib.define("nms(Tensor dets, Tensor scores, float iou_threshold) -> Tensor")
    except Exception:
        return

    _TORCHVISION_NMS_LIB = lib


def clear_partial_imports() -> None:
    prefixes = ("docling.", "torchvision.", "transformers.")
    for name in list(sys.modules):
        if name in {"docling", "torchvision", "transformers"} or name.startswith(prefixes):
            sys.modules.pop(name, None)


def import_docling_types() -> tuple[Any, Any, Any, Any]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    return DocumentConverter, PdfFormatOption, InputFormat, PdfPipelineOptions


def load_docling_types() -> tuple[Any, Any, Any, Any]:
    try:
        return import_docling_types()
    except Exception as exc:
        if not has_torchvision_nms_issue(exc):
            raise

        patch_torchvision_nms_import_issue()
        clear_partial_imports()
        return import_docling_types()


def build_document_converter() -> Any:
    global _DOCUMENT_CONVERTER

    with _DOCUMENT_CONVERTER_LOCK:
        if _DOCUMENT_CONVERTER is None:
            _DOCUMENT_CONVERTER = create_document_converter()
        return _DOCUMENT_CONVERTER


def create_document_converter() -> Any:
    DocumentConverter, PdfFormatOption, InputFormat, PdfPipelineOptions = load_docling_types()

    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = False

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        },
    )


def warmup_document_converter() -> None:
    converter = build_document_converter()
    _, _, InputFormat, _ = load_docling_types()
    converter.initialize_pipeline(InputFormat.PDF)


def warmup_document_converter_safely() -> None:
    try:
        warmup_document_converter()
    except Exception:
        _LOGGER.exception("Docling converter warmup failed")


def start_document_converter_warmup() -> None:
    global _DOCUMENT_CONVERTER_WARMUP_STARTED

    with _DOCUMENT_CONVERTER_LOCK:
        if _DOCUMENT_CONVERTER_WARMUP_STARTED:
            return
        _DOCUMENT_CONVERTER_WARMUP_STARTED = True

    thread = threading.Thread(
        target=warmup_document_converter_safely,
        name="docling-converter-warmup",
        daemon=True,
    )
    thread.start()


def find_libreoffice_executable() -> str:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        raise ValueError("LibreOffice was not found. Install libreoffice-writer first.")
    return executable


def convert_docx_to_pdf(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="homepage-docling-lo-") as temp_dir:
        temp_path = Path(temp_dir)
        profile_dir = temp_path / "profile"
        out_dir = temp_path / "out"
        profile_dir.mkdir()
        out_dir.mkdir()

        command = [
            find_libreoffice_executable(),
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--convert-to",
            libreoffice_pdf_export_filter(),
            "--outdir",
            str(out_dir),
            str(input_path),
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        generated_pdf = out_dir / f"{input_path.stem}.pdf"

        if result.returncode != 0 or not generated_pdf.exists():
            details = "\n".join(part for part in [result.stdout, result.stderr] if part)
            raise RuntimeError(
                f"LibreOffice failed to convert DOCX to PDF.\n{details}".strip()
            )

        shutil.move(str(generated_pdf), output_path)

    return output_path


def libreoffice_pdf_export_filter() -> str:
    options = json.dumps(LIBREOFFICE_PDF_EXPORT_OPTIONS, separators=(",", ":"))
    return f"pdf:writer_pdf_Export:{options}"


def remove_docx_headers_footers(input_path: Path, output_path: Path) -> Path:
    from docx import Document

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = Document(input_path)

    for section in document.sections:
        parts = [
            section.header,
            section.first_page_header,
            section.even_page_header,
            section.footer,
            section.first_page_footer,
            section.even_page_footer,
        ]

        for part in parts:
            part.is_linked_to_previous = False
            clear_docx_story_part(part)

    document.save(output_path)
    return output_path


def clear_docx_story_part(story_part: Any) -> None:
    element = story_part._element

    for child in list(element):
        element.remove(child)

    story_part.add_paragraph()


def convert_to_json_data(input_path: Path) -> dict[str, Any]:
    converter = build_document_converter()
    result = converter.convert(input_path)
    return result.document.export_to_dict()


def convert_docx_to_python_docx_json_data(input_path: Path, file_id: str) -> dict[str, Any]:
    from src.services.python_docx_contract_parser import parse_docx_contract_to_json_data

    return parse_docx_contract_to_json_data(input_path, doc_id=file_id)


def convert_pdf_to_pymupdf4llm_json_data(input_path: Path, file_id: str) -> dict[str, Any]:
    from src.services.pdf_contract_parser import parse_pymupdf4llm_pdf_to_json_data

    return parse_pymupdf4llm_pdf_to_json_data(input_path, doc_id=file_id)


def add_docling_pdf_contract_structure(
    json_data: dict[str, Any],
    input_path: Path,
    file_id: str,
) -> dict[str, Any]:
    from src.services.pdf_contract_parser import add_contract_structure_to_docling_pdf_json_data

    return add_contract_structure_to_docling_pdf_json_data(
        json_data,
        source_file=input_path.name,
        doc_id=file_id,
    )


def normalize_docx_parser_engine(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized not in {"docling", "python-docx", "pymupdf4llm"}:
        raise ParsingError("UNSUPPORTED_DOCX_PARSER_ENGINE", status_code=500)
    return normalized


def normalize_pdf_parser_engine(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized not in {"docling", "pymupdf4llm"}:
        raise ParsingError("UNSUPPORTED_PDF_PARSER_ENGINE", status_code=500)
    return normalized


def write_json_atomically(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".part")
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path.write_text(json_text + "\n", encoding="utf-8")
    temp_path.replace(path)
