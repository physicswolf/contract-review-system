from pathlib import Path
from uuid import uuid4

from src.config import get_settings
from src.services.document_parser import parse_uploaded_document

settings = get_settings()
source = Path("../data/物资采购合同-物资采购通用合同.pdf").resolve()
file_id = str(uuid4())

artifacts = parse_uploaded_document(source, file_id, source.suffix, settings)
print(artifacts.json_path)
