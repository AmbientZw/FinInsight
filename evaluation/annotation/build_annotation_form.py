# -*- coding: utf-8 -*-
"""生成盲评标注表单（人工标注用，课题要求 2–3 名标注员）。

用法：
  python build_annotation_form.py [每档样本数] [随机种子]

产出（都在本目录下）：
  - annotation_form.md       盲评阅读材料：匿名ID + 原文 + 摘要（**不含**真实标签/ID）
  - annotation_template.csv  录入模板：`匿名ID, 评级(好/中/差)`，评级留空待填
  - annotation_key.json      匿名ID → 真实 sample_id / quality_level 的映射（**勿发给标注员**）

设计要点：
  1. 盲评：sample_id 形如 R001_good / R001_bad，本身泄露标签，故映射为 A01.. 匿名ID；
  2. 分层抽样：good / medium / bad 各取 N 篇，且同一份研报（report_id）不重复出现，
     避免标注员看到「同一原文两份摘要」而产生配对暗示；
  3. 只评 good/medium/bad 三档（对抗样本走独立的客观对抗验证，不进入人工标注）。
"""
import json
import random
import sys
from pathlib import Path

ANNOTATION_DIR = Path(__file__).resolve().parent
SAMPLES_FILE = ANNOTATION_DIR.parent / "samples" / "golden" / "summary_samples.jsonl"

TIERS = ("good", "medium", "bad")  # 只评三档


def load_samples() -> list[dict]:
    samples = []
    with open(SAMPLES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def build_form(n_per_tier: int = 6, seed: int = 42):
    samples = load_samples()
    rng = random.Random(seed)

    # 按档分组，并按 report_id 去重以保证每份研报只出现一次
    by_tier = {t: {} for t in TIERS}
    for s in samples:
        if s["quality_level"] in TIERS:
            by_tier[s["quality_level"]][s["report_id"]] = s

    selected = []
    used_reports = set()
    for tier in TIERS:
        pool = [s for rid, s in by_tier[tier].items() if rid not in used_reports]
        rng.shuffle(pool)
        picked = pool[:n_per_tier]
        for s in picked:
            used_reports.add(s["report_id"])
        selected.extend(picked)

    # 打乱顺序，赋予匿名 ID
    rng.shuffle(selected)
    anonymous = [f"A{i:02d}" for i in range(1, len(selected) + 1)]

    key = {}
    for aid, s in zip(anonymous, selected):
        key[aid] = {
            "sample_id": s["sample_id"],
            "report_id": s["report_id"],
            "quality_level": s["quality_level"],
        }

    return selected, anonymous, key


def render_markdown(selected, anonymous) -> str:
    lines = [
        "# 盲评标注材料（请勿传播本文件之外的内容）",
        "",
        f"共 {len(selected)} 份研报摘要，每份包含「原文」与「结构化摘要」。",
        "请对照原文，按《标注指南》把每份摘要的整体质量评为 **好 / 中 / 差** 三档之一。",
        "",
        "> 材料中不含任何真实质量标签；匿名 ID（A01..）仅用于回填录入表。",
        "",
        "---",
    ]
    for aid, s in zip(anonymous, selected):
        try:
            pretty = json.dumps(json.loads(s["output"]), ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            pretty = s["output"]
        lines.append(f"## {aid}")
        lines.append("")
        lines.append("**原文**")
        lines.append("")
        lines.append(s["source_text"])
        lines.append("")
        lines.append("**摘要**")
        lines.append("")
        lines.append("```json")
        lines.append(pretty)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def write_template(anonymous) -> None:
    """录入模板：匿名ID + 空评级列。"""
    path = ANNOTATION_DIR / "annotation_template.csv"
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("匿名ID,评级(好/中/差)\n")
        for aid in anonymous:
            f.write(f"{aid},\n")
    print(f"录入模板 → {path.name}（复制一份，每位标注员填自己的评级）")


def main():
    n_per_tier = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    selected, anonymous, key = build_form(n_per_tier, seed)

    form_path = ANNOTATION_DIR / "annotation_form.md"
    form_path.write_text(render_markdown(selected, anonymous), encoding="utf-8")

    key_path = ANNOTATION_DIR / "annotation_key.json"
    key_path.write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

    write_template(anonymous)

    # 统计
    from collections import Counter
    dist = Counter(s["quality_level"] for s in selected)
    print(f"已生成盲评表单：{len(selected)} 份样本")
    print(f"  分层分布：{dict(dist)}（每档 {n_per_tier} 篇，report_id 不重复）")
    print(f"  盲评材料 → {form_path.name}")
    print(f"  匿名映射 → {key_path.name}（**仅分析时用，勿发给标注员**）")


if __name__ == "__main__":
    main()
