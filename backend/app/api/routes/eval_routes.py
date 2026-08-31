import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.routes.reports import get_report_text
from app.core.schemas import StructuredSummary
from app.services.eval_service import evaluate_summary_stream

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/{report_id}/stream")
async def evaluate_report_stream(report_id: str, summary: StructuredSummary):
    """对生成的摘要做 7 维评测，流式返回各维度得分（测试阶段展示评分过程）。"""
    text = get_report_text(report_id)

    def event_generator():
        try:
            for event in evaluate_summary_stream(text, summary):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:  # noqa: BLE001
            yield "data: [ERROR] " + json.dumps(str(e), ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
