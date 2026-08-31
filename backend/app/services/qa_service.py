from app.core.llm_client import hy3_client, DISCLAIMER
from app.core.prompts import QA_SYSTEM_PROMPT, QA_USER_PROMPT
from app.core.schemas import QAResponse


def answer_question(
    report_text: str,
    question: str,
    reasoning_effort: str = "low",
) -> QAResponse:
    """Answer a question based on report content."""
    messages = [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": QA_USER_PROMPT.format(
                report_text=report_text, question=question
            ),
        },
    ]

    answer = hy3_client.generate(
        messages=messages,
        reasoning_effort=reasoning_effort,
        temperature=0.3,
        max_tokens=16000,
    )

    return QAResponse(
        answer=answer,
        sources=[],
        disclaimer=DISCLAIMER,
    )


def answer_question_stream(
    report_text: str,
    question: str,
    reasoning_effort: str = "low",
):
    """Stream answer to a question based on report content."""
    messages = [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": QA_USER_PROMPT.format(
                report_text=report_text, question=question
            ),
        },
    ]

    return hy3_client.generate_stream(
        messages=messages,
        reasoning_effort=reasoning_effort,
        temperature=0.3,
        max_tokens=16000,
    )
