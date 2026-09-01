import json

from app.core.llm_client import hy3_client, DISCLAIMER
from app.core.number_audit import verify_flags
from app.core.prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT
from app.core.schemas import Chart, ChartPoint, StructuredSummary

_ALLOWED_CHART_TYPES = {"bar", "line", "pie"}


def _summary_messages(report_text: str) -> list[dict]:
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SUMMARY_USER_PROMPT.format(report_text=report_text),
        },
    ]


def _parse_charts(raw_charts) -> list[Chart]:
    """把模型输出的 charts 字段安全地解析为 Chart 列表，非法条目丢弃（不阻断摘要）。"""
    if not isinstance(raw_charts, list):
        return []
    charts: list[Chart] = []
    for c in raw_charts[:4]:
        if not isinstance(c, dict):
            continue
        points: list[ChartPoint] = []
        raw_data = c.get("data")
        if isinstance(raw_data, list):
            for p in raw_data[:12]:
                if not isinstance(p, dict):
                    continue
                try:
                    value = float(p.get("value"))
                except (TypeError, ValueError):
                    continue
                label = str(p.get("label", "")).strip()
                if label:
                    points.append(ChartPoint(label=label, value=value))
        if not points:
            continue
        chart_type = str(c.get("chart_type", "bar")).lower()
        if chart_type not in _ALLOWED_CHART_TYPES:
            chart_type = "bar"
        charts.append(
            Chart(
                chart_type=chart_type,
                title=str(c.get("title", "")).strip(),
                unit=str(c.get("unit", "")).strip(),
                data=points,
            )
        )
    return charts


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

    summary = StructuredSummary(
        core_conclusions=data.get("core_conclusions", []),
        key_data=data.get("key_data", []),
        main_risks=data.get("main_risks", []),
        investment_advice=data.get("investment_advice", []),
        points_to_verify=data.get("points_to_verify", []),
        disclaimer=data.get("disclaimer", DISCLAIMER),
        charts=_parse_charts(data.get("charts", [])),
    )

    # 确定性数字校验：把与原文对不上的数字兜底标进疑点（不依赖模型自觉）
    flags = verify_flags(report_text, cleaned)
    if flags:
        summary.points_to_verify = [*summary.points_to_verify, *flags]
    return summary


def generate_summary_stream(report_text: str):
    """流式生成结构化摘要（返回 OpenAI stream 迭代器，供 SSE 消费）。"""
    return hy3_client.generate_stream(
        messages=_summary_messages(report_text),
        reasoning_effort="low",
        temperature=0.3,
        max_tokens=16000,
    )
