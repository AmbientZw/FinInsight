import json

from app.core.llm_client import hy3_client, DISCLAIMER
from app.core.prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT
from app.core.schemas import StructuredSummary


def _summary_messages(report_text: str) -> list[dict]:
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SUMMARY_USER_PROMPT.format(report_text=report_text),
        },
    ]


def generate_summary(report_text: str) -> StructuredSummary:
    """Generate a structured summary from report text using Hy3."""
    raw = hy3_client.generate(
        messages=_summary_messages(report_text),
        reasoning_effort="low",
        temperature=0.3,
        max_tokens=16000,
    )

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return StructuredSummary(
            core_conclusions=[raw[:500]],
            key_data=[],
            main_risks=[],
            investment_advice=[],
            points_to_verify=["JSON解析失败，请检查模型输出格式"],
            disclaimer=DISCLAIMER,
        )

    return StructuredSummary(
        core_conclusions=data.get("core_conclusions", []),
        key_data=data.get("key_data", []),
        main_risks=data.get("main_risks", []),
        investment_advice=data.get("investment_advice", []),
        points_to_verify=data.get("points_to_verify", []),
        disclaimer=data.get("disclaimer", DISCLAIMER),
    )


def generate_summary_stream(report_text: str):
    """流式生成结构化摘要（返回 OpenAI stream 迭代器，供 SSE 消费）。"""
    return hy3_client.generate_stream(
        messages=_summary_messages(report_text),
        reasoning_effort="low",
        temperature=0.3,
        max_tokens=16000,
    )
