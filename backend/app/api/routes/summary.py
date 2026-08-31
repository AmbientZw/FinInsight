import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.routes.reports import get_report_text
from app.core.schemas import StructuredSummary
from app.services.summary_service import generate_summary, generate_summary_stream

router = APIRouter(prefix="/summary", tags=["summary"])


@router.post("/{report_id}", response_model=StructuredSummary)
async def create_summary(report_id: str):
    text = get_report_text(report_id)
    return generate_summary(text)


@router.post("/{report_id}/stream")
async def create_summary_stream(report_id: str):
    """流式返回摘要原始输出（SSE），前端累积后解析为结构化摘要。"""
    text = get_report_text(report_id)
    stream = generate_summary_stream(text)

    def event_generator():
        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield (
                        "data: "
                        + json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
                        + "\n\n"
                    )
            yield "data: [DONE]\n\n"
        except Exception as e:  # noqa: BLE001
            yield "data: [ERROR] " + json.dumps(str(e), ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
