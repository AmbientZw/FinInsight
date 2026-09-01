"""确定性数字校验（D3「数据精确性」的代码裁决层）。

复用 D3 评测器相同的「数字+单位」正则，把生成摘要里的数字与原文逐字符比对，
返回原文中找不到的「数字+单位」串。用于生成后兜底标注疑点，而不是依赖模型自觉
（对应「模型提议、代码裁决」的分工）。
"""
import re

# 与 evaluation/scripts/evaluators/rules.py 的 D3 保持一致（长单位在前，避免"万亿元"被截成"万"）
_NUM_UNIT_RE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(万亿元|千亿元|百亿元|十亿元|亿元|"
    r"千万元|百万元|十万元|万元|亿美元|美元|港元|"
    r"万亿|亿|万|元|%|％|倍|点)"
)


def audit_numbers(source_text: str, output_text: str) -> list[str]:
    """返回 output_text 中无法在 source_text 里逐字符匹配到的「数字+单位」串（去重保序）。"""
    source_norm = re.sub(r"[,\s]", "", source_text)
    mismatches: list[str] = []
    seen: set[str] = set()
    for m in _NUM_UNIT_RE.finditer(output_text):
        full = re.sub(r"[,\s]", "", m.group(0))
        if full and full not in source_norm and full not in seen:
            seen.add(full)
            mismatches.append(m.group(0))
    return mismatches


def verify_flags(source_text: str, output_text: str, limit: int = 6) -> list[str]:
    """返回可直接追加进 points_to_verify 的疑点字符串。"""
    return [
        f"数值校验：{num} 未在原文中逐字出现，请核实"
        for num in audit_numbers(source_text, output_text)[:limit]
    ]
