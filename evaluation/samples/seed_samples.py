"""构建评测样本集：Good/Medium/Bad 三级样本 + 对抗样本。

Good 样本通过调用 Hy3 生成真实摘要；
Medium/Bad/对抗样本通过程序化注入错误构造，避免额外 API 调用。

输出：evaluation/samples/golden/summary_samples.jsonl
"""

import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 加载 backend/.env
BACKEND_ENV = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
load_dotenv(BACKEND_ENV)

import os

from report_data import REPORTS, render_report

SAMPLES_DIR = Path(__file__).resolve().parent / "golden"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 摘要生成 system prompt（与后端一致）
SUMMARY_SYSTEM_PROMPT = """你是一位资深金融研究员，擅长从行业研报和上市公司年报中提取关键信息。
你的任务是对给定的研报内容生成结构化摘要。

## 输出要求
请严格按照以下 JSON 格式输出，不要添加任何额外文字：
{
  "core_conclusions": ["结论1（来源：第X页）"],
  "key_data": ["关键数据1：具体数值（来源：第X页）"],
  "main_risks": ["风险1（来源：第X页）"],
  "investment_advice": ["建议1（来源：第X页）"],
  "points_to_verify": ["疑点1：需要进一步核实的内容及原因"],
  "disclaimer": "⚠️ 免责声明：本分析由AI模型自动生成，仅供参考，不构成任何投资建议。投资有风险，决策需谨慎。"
}

## 规则
1. 每条结论、数据、风险均须标注原文出处（页码或段落位置）
2. 关键数据必须精确引用原文数值，不可四舍五入或估算
3. 必须包含免责声明
4. 不得出现"必涨"、"保证收益"等越界承诺
5. 如发现原文中存在矛盾数据或模糊表述，请在"points_to_verify"中标注"""


def get_client():
    api_key = os.environ.get("HY3_API_KEY", "")
    base_url = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    model = os.environ.get("HY3_MODEL", "hy3")
    return OpenAI(api_key=api_key, base_url=base_url), model


def generate_good(client, model, report_text: str) -> str:
    """调用 Hy3 生成真实结构化摘要（JSON 字符串）。"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"请对以下研报内容生成结构化摘要：\n\n{report_text}"},
        ],
        temperature=0.3,
        max_tokens=4096,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )
    raw = response.choices[0].message.content or ""
    # 清理 markdown 代码块包裹
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
    return cleaned.strip()


# ============ 错误注入函数 ============

def _load_json(output: str) -> dict | None:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def inject_number_error(data: dict, n: int) -> dict:
    """在 key_data 和 core_conclusions 中篡改 n 个数字。"""
    import random
    random.seed(42)
    changed = 0

    def _mutate_num(s: str) -> str:
        """找到一个数字并放大/缩小。"""
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            orig = float(m.group(1).replace(",", ""))
            new_val = orig * 1.8 + 3
            new_str = f"{new_val:.1f}".rstrip("0").rstrip(".")
            return s[: m.start()] + new_str + s[m.end():]
        return s

    for field in ["key_data", "core_conclusions"]:
        items = data.get(field, [])
        for i in range(len(items)):
            if changed >= n:
                break
            items[i] = _mutate_num(items[i])
            changed += 1
        data[field] = items
    return data


def remove_field(data: dict, field: str) -> dict:
    if field in data:
        del data[field]
    return data


def remove_citations(data: dict, n: int) -> dict:
    """删除 n 条次要条目的出处标注（追溯性瑕疵），不触碰任何数字。

    用于构造「中」档：数字保持 100% 正确，仅让个别条目缺「（来源：第X页）」标注，
    模拟真实世界中"数据对、但出处标注不严谨"的中间档质量。
    """
    import random
    random.seed(42)
    removed = 0
    for field in ["key_data", "main_risks", "investment_advice", "core_conclusions"]:
        items = data.get(field, [])
        for i in range(len(items)):
            if removed >= n:
                break
            new_item = re.sub(r"（来源[：:]\s*第\s*\d+\s*页）", "", items[i])
            if new_item != items[i]:
                items[i] = new_item
                removed += 1
        data[field] = items
    return data


def corrupt_structure(output: str) -> str:
    """破坏 JSON 结构，输出为自由文本。"""
    data = _load_json(output)
    if not data:
        return output
    # 拼接成无结构的自由文本
    parts = []
    for k, v in data.items():
        if isinstance(v, list):
            parts.append(f"{k}方面，有以下几点需要注意")
            for item in v:
                parts.append(item)
        else:
            parts.append(str(v))
    return "\n".join(parts)


def remove_disclaimer(data: dict) -> dict:
    if "disclaimer" in data:
        data["disclaimer"] = ""
    return data


def mix_foreign_data(data: dict, other_report: dict) -> dict:
    """混入其他研报的数据。"""
    other = render_report(other_report)
    # 从其他研报提取一个数字
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万辆|亿元|亿美元|%)", other)
    if m and data.get("key_data"):
        foreign = m.group(0)
        data["key_data"][0] = f"{foreign}（来源：第1页）"
    return data


# ============ 对抗样本构造 ============

PADDING_TEXT = (
    "此外，从更宏观的视角来看，这一情况具有重要的参考价值和深远影响，"
    "值得从业者持续关注和深入研究。同时，我们也需要认识到，行业的发展是一个复杂的动态过程，"
    "受到多重因素的共同作用，任何单一维度的分析都难以全面把握其全貌。"
)


def length_padding(data: dict) -> dict:
    """在核心结论中填充无意义但看似专业的内容。"""
    if "core_conclusions" in data:
        for i in range(len(data["core_conclusions"])):
            data["core_conclusions"][i] += " " + PADDING_TEXT
    return data


JARGON = "结合PE/PB估值模型与DCF折现分析，该标的估值中枢存在系统性上移空间，"
JARGON2 = "从CAPM资本资产定价模型看，其风险溢价具备配置价值，"


def jargon_stuffing(data: dict) -> dict:
    """插入语境不当的专业术语。"""
    if "core_conclusions" in data and len(data["core_conclusions"]) > 0:
        data["core_conclusions"][0] = JARGON + data["core_conclusions"][0]
        data["core_conclusions"].insert(1, JARGON2 + "预期回报率显著高于无风险利率。")
    return data


def fake_citation(data: dict) -> dict:
    """伪造精确数据引用。"""
    fake = "根据报告第23页，2024年Q3营收同比增长45.3%，净利润率提升至28.7%"
    if "key_data" in data:
        data["key_data"].append(f"{fake}（来源：第23页）")
    return data


# ============ 主流程 ============

def build_samples():
    client, model = get_client()
    all_samples = []

    good_outputs = {}

    # 1. 生成 Good 样本（20 个，调用 Hy3）
    print("=== 生成 Good 样本 ===")
    for idx, report in enumerate(REPORTS):
        report_text = render_report(report)
        print(f"  [{idx+1}/20] {report['id']} {report['title'][:20]}...")
        try:
            raw = generate_good(client, model, report_text)
            good_outputs[report["id"]] = raw
            all_samples.append({
                "sample_id": f"{report['id']}_good",
                "report_id": report["id"],
                "industry": report["industry"],
                "difficulty": report["difficulty"],
                "quality_level": "good",
                "source_text": report_text,
                "output": raw,
            })
        except Exception as e:
            print(f"    生成失败: {e}")
        time.sleep(0.5)  # 限速

    # 2. 构造 Medium 样本（注入 1-2 处轻微错误）
    print("\n=== 构造 Medium 样本 ===")
    for report in REPORTS:
        raw = good_outputs.get(report["id"])
        if not raw:
            continue
        data = _load_json(raw)
        if not data:
            continue
        # 「中」= 数字正确 + 非致命追溯/完整性瑕疵（不注入数字错误——
        # 金融场景对数字错误零容忍，「错 1 处」≈「错 3 处」都会被视为「差」）
        medium = remove_citations(data, 2)              # 删 2 条出处标注 → 追溯性瑕疵
        medium = remove_field(medium, "points_to_verify")  # 删次要字段 → 完整性瑕疵
        all_samples.append({
            "sample_id": f"{report['id']}_medium",
            "report_id": report["id"],
            "industry": report["industry"],
            "difficulty": report["difficulty"],
            "quality_level": "medium",
            "source_text": render_report(report),
            "output": _dump(medium),
        })

    # 3. 构造 Bad 样本（注入 3+ 严重错误 / 破坏结构 / 删免责声明）
    print("\n=== 构造 Bad 样本 ===")
    for i, report in enumerate(REPORTS):
        raw = good_outputs.get(report["id"])
        if not raw:
            continue
        data = _load_json(raw)
        if not data:
            continue
        bad = inject_number_error(data, 4)
        bad = remove_disclaimer(bad)
        # 混入其他研报数据
        other = REPORTS[(i + 5) % len(REPORTS)]
        bad = mix_foreign_data(bad, other)

        # 每第 3 个样本破坏 JSON 结构
        if i % 3 == 0:
            output = corrupt_structure(_dump(bad))
        else:
            output = _dump(bad)

        all_samples.append({
            "sample_id": f"{report['id']}_bad",
            "report_id": report["id"],
            "industry": report["industry"],
            "difficulty": report["difficulty"],
            "quality_level": "bad",
            "source_text": render_report(report),
            "output": output,
        })

    # 4. 构造对抗样本（15 个：长度注水/术语堆砌/伪造引用 各 5 个）
    print("\n=== 构造对抗样本 ===")
    adversarial_types = [
        ("length_padding", length_padding, "长度注水"),
        ("jargon_stuffing", jargon_stuffing, "术语堆砌"),
        ("fake_citation", fake_citation, "伪造引用"),
    ]
    for adv_type, adv_func, adv_name in adversarial_types:
        for j in range(5):
            report = REPORTS[j]  # 取前 5 篇
            raw = good_outputs.get(report["id"])
            if not raw:
                continue
            data = _load_json(raw)
            if not data:
                continue
            adv_data = adv_func(json.loads(json.dumps(data)))  # 深拷贝
            all_samples.append({
                "sample_id": f"{report['id']}_adv_{adv_type}",
                "report_id": report["id"],
                "industry": report["industry"],
                "difficulty": report["difficulty"],
                "quality_level": f"adversarial_{adv_type}",
                "source_text": render_report(report),
                "output": _dump(adv_data),
            })

    # 5. 写入 JSONL
    out_path = SAMPLES_DIR / "summary_samples.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\n=== 完成 ===")
    print(f"共生成 {len(all_samples)} 个样本，保存至 {out_path}")

    # 统计
    from collections import Counter
    counter = Counter(s["quality_level"] for s in all_samples)
    for k, v in counter.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    build_samples()
