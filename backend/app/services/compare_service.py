"""多报告对比服务：将多份结构化摘要送入 Hy3 做交叉对比与矛盾检测。"""

from app.core.llm_client import hy3_client
from app.core.prompts import COMPARE_SYSTEM_PROMPT, COMPARE_USER_PROMPT
from app.core.schemas import CompareReportInput


def _flatten_summary(report: CompareReportInput) -> str:
    """把一份结构化摘要拍平成可读文本块。"""
    lines = [f"### 报告：{report.title}"]
    for label, items in (
        ("核心结论", report.summary.core_conclusions),
        ("关键数据", report.summary.key_data),
        ("主要风险", report.summary.main_risks),
        ("投资建议", report.summary.investment_advice),
        ("待核实疑点", report.summary.points_to_verify),
    ):
        if items:
            lines.append(f"**{label}**")
            lines.extend(f"- {x}" for x in items)
    return "\n".join(lines)


def _compare_messages(reports: list[CompareReportInput]) -> list[dict]:
    joined = "\n\n".join(_flatten_summary(r) for r in reports)
    return [
        {"role": "system", "content": COMPARE_SYSTEM_PROMPT},
        {"role": "user", "content": COMPARE_USER_PROMPT.format(reports=joined)},
    ]


def compare_summaries_stream(reports: list[CompareReportInput]):
    """流式返回对比分析（返回 OpenAI stream 迭代器，供 SSE 消费）。"""
    return hy3_client.generate_stream(
        messages=_compare_messages(reports),
        reasoning_effort="low",
        temperature=0.3,
        max_tokens=16000,
    )
