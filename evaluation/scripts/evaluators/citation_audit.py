"""D2（证据可追溯性）确定性引用审计。

采用「模型提议、代码裁决」的分工：LLM Judge 判「引用质量」，这里用确定性规则裁决
「引用是否存在、页码是否真实」，并对 LLM 分数设封顶——补齐「删除出处标注」类坏样本
的判别力缺口。
"""
import json
import re

# 匹配「（来源：第X页）」/「（来源:第X页）」
_CITATION_RE = re.compile(r"（来源[：:]\s*第\s*([0-9]+)\s*页）")

_LIST_FIELDS = (
    "core_conclusions",
    "key_data",
    "main_risks",
    "investment_advice",
    "points_to_verify",
)


def _extract_items(output_text: str) -> list[str]:
    """从 JSON 摘要提取各 list 字段的全部条目。"""
    items: list[str] = []
    try:
        data = json.loads(output_text)
    except (json.JSONDecodeError, TypeError):
        return items
    if not isinstance(data, dict):
        return items
    for field in _LIST_FIELDS:
        val = data.get(field)
        if isinstance(val, list):
            items.extend(str(x) for x in val if x)
    return items


def audit_citations(source_text: str, output_text: str) -> dict:
    """返回引用审计结果：覆盖率、无效页码、确定性封顶分（ceiling）。"""
    items = _extract_items(output_text)
    if not items:
        return {
            "coverage": None,
            "total_items": 0,
            "cited_items": 0,
            "invalid_pages": [],
            "ceiling": 1.0,
            "reason": "输出无可解析条目，视为无出处",
        }

    cited = 0
    invalid_pages: list[int] = []
    for item in items:
        m = _CITATION_RE.search(item)
        if m:
            cited += 1
            page = int(m.group(1))
            if f"第{page}页" not in source_text:
                invalid_pages.append(page)

    coverage = cited / len(items)

    # 确定性封顶：越严重的缺陷封得越低
    if coverage == 0.0:
        ceiling, reason = 1.0, "所有条目均无出处标注"
    elif invalid_pages:
        ceiling, reason = 2.0, f"存在指向原文不存在页码的引用: {invalid_pages}"
    elif coverage < 1.0:
        ceiling, reason = 3.0, f"仅 {cited}/{len(items)} 条目标注出处"
    else:
        ceiling, reason = 5.0, "全部条目均标注有效出处（不封顶）"

    return {
        "coverage": round(coverage, 3),
        "total_items": len(items),
        "cited_items": cited,
        "invalid_pages": invalid_pages,
        "ceiling": ceiling,
        "reason": reason,
    }
