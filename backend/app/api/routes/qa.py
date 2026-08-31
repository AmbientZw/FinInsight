import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.routes.reports import get_report_text
from app.core.schemas import QARequest, QAResponse
from app.services.qa_service import answer_question, answer_question_stream

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/", response_model=QAResponse)
async def ask_question(req: QARequest):
    text = get_report_text(req.report_id)
    return answer_question(text, req.question, req.reasoning_effort)


@router.post("/stream")
async def ask_question_stream(req: QARequest):
    text = get_report_text(req.report_id)
    stream = answer_question_stream(text, req.question, req.reasoning_effort)

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
