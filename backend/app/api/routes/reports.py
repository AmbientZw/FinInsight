import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException

from app.config import settings
from app.core.parser import extract_text_from_pdf
from app.core.schemas import ReportMeta

router = APIRouter(prefix="/reports", tags=["reports"])

_reports_store: dict[str, dict] = {}


@router.post("/upload", response_model=ReportMeta)
async def upload_report(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")

    report_id = uuid.uuid4().hex[:12]
    save_path = settings.upload_dir / f"{report_id}.pdf"
    content = await file.read()

    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {settings.max_upload_size_mb}MB 限制")

    save_path.write_bytes(content)

    parsed = extract_text_from_pdf(save_path)

    _reports_store[report_id] = {
        "meta": {
            "id": report_id,
            "filename": file.filename,
            "title": file.filename.rsplit(".", 1)[0],
            "page_count": parsed["page_count"],
            "char_count": parsed["char_count"],
        },
        "full_text": parsed["full_text"],
        "pdf_path": str(save_path),
    }

    return ReportMeta(**_reports_store[report_id]["meta"])


@router.get("/{report_id}", response_model=ReportMeta)
async def get_report(report_id: str):
    if report_id not in _reports_store:
        raise HTTPException(404, "报告不存在")
    return ReportMeta(**_reports_store[report_id]["meta"])


@router.get("/", response_model=list[ReportMeta])
async def list_reports():
    return [ReportMeta(**r["meta"]) for r in _reports_store.values()]


def get_report_text(report_id: str) -> str:
    if report_id not in _reports_store:
        raise HTTPException(404, "报告不存在")
    return _reports_store[report_id]["full_text"]
