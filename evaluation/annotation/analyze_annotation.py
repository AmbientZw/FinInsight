# -*- coding: utf-8 -*-
"""合并标注结果，计算多标注员一致性（Fleiss' κ）与「评估分 vs 人工标注」相关。

用法（先把标注员填好的 CSV 放在本目录，命名 `annotation_<名字>.csv`）：
  python analyze_annotation.py

输入：
  - annotation_*.csv   每位标注员一份：`匿名ID,评级(好/中/差)`（自动排除模板 annotation_template.csv）
  - annotation_key.json 匿名ID → 真实 sample_id / quality_level
  - ../results/eval_table.csv  系统自动评测结果（用于 Spearman 相关）

输出：
  - 终端打印：Fleiss' κ、各样本多数档位、Spearman ρ
  - annotation_report.json 落盘
"""
import glob
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ANNOTATION_DIR = Path(__file__).resolve().parent
RESULTS_DIR = ANNOTATION_DIR.parent / "results"

LEVEL_ORDINAL = {"好": 2, "中": 1, "差": 0}
TRUTH_TO_ZH = {"good": "好", "medium": "中", "bad": "差"}


def load_annotation_files() -> list[tuple[str, dict[str, str]]]:
    """返回 [(标注员名, {匿名ID: 评级})]."""
    files = [
        p for p in glob.glob(str(ANNOTATION_DIR / "annotation_*.csv"))
        if "template" not in Path(p).name
    ]
    if not files:
        raise FileNotFoundError(
            "未找到标注结果。请将每位标注员填好的 CSV 命名为 annotation_<名字>.csv 放入本目录。"
        )
    parsed = []
    for p in files:
        name = Path(p).stem.replace("annotation_", "")
        ratings = {}
        for row in pd.read_csv(p).itertuples(index=False):
            aid = str(getattr(row, row._fields[0])).strip()
            rating = str(getattr(row, row._fields[1])).strip()
            if aid and rating:
                ratings[aid] = rating
        parsed.append((name, ratings))
    return parsed


def fleiss_kappa(matrix: np.ndarray) -> float:
    """matrix: N 样本 × k 类别 的计次矩阵（每行和为标注员数）。"""
    n = matrix.sum(axis=1)[0]          # 每样本的标注员数
    N = matrix.shape[0]
    k = matrix.shape[1]
    p_j = matrix.sum(axis=0) / (N * n)
    P_i = (np.sum(matrix ** 2, axis=1) - n) / (n * (n - 1))
    P_bar = P_i.mean()
    P_e = np.sum(p_j ** 2)
    if abs(1 - P_e) < 1e-9:
        return float("nan")
    return (P_bar - P_e) / (1 - P_e)


def main():
    key = json.loads((ANNOTATION_DIR / "annotation_key.json").read_text(encoding="utf-8"))
    annotators = load_annotation_files()
    print(f"读取到 {len(annotators)} 位标注员：{[n for n, _ in annotators]}\n")

    # 对齐成矩阵：行=匿名ID，列=标注员
    aids = sorted(key.keys())
    n_raters = len(annotators)
    ratings_matrix = []   # 好/中/差 文本
    for aid in aids:
        row = []
        for _, r in annotators:
            val = r.get(aid, "")
            if val not in LEVEL_ORDINAL:
                raise ValueError(f"非法评级：{aid} 的「{val}」，只允许 好/中/差")
            row.append(val)
        ratings_matrix.append(row)

    # 一致性：Fleiss' κ
    cats = list(LEVEL_ORDINAL.keys())
    counts = np.zeros((len(aids), len(cats)), dtype=int)
    for i, row in enumerate(ratings_matrix):
        for j, c in enumerate(cats):
            counts[i, j] = row.count(c)
    kappa = fleiss_kappa(counts)
    print(f"Fleiss' κ（{n_raters} 标注员 × 三档） = {kappa:.3f}")
    print(f"  解读：>0.6 基本一致；>0.8 高度一致；<0.4 说明标准需更明确\n")

    # 评估分 vs 人工标注 相关
    eval_df = pd.read_csv(RESULTS_DIR / "eval_table.csv")
    if "封顶后总分" in eval_df.columns:
        eval_df["总分"] = eval_df["封顶后总分"]
    eval_score = {}
    for _, r in eval_df.iterrows():
        eval_score[str(r["sample_id"])] = float(r["总分"])

    mean_ordinal = []
    majority = []
    for i, aid in enumerate(aids):
        ords = [LEVEL_ORDINAL[v] for v in ratings_matrix[i]]
        mean_ordinal.append(float(np.mean(ords)))
        # 多数档位（平票取更高档，更保守地视为质量较高）
        cnt = {c: ratings_matrix[i].count(c) for c in cats}
        best = max(cnt, key=lambda c: (cnt[c], LEVEL_ORDINAL[c]))
        majority.append(best)

    sample_ids = [key[aid]["sample_id"] for aid in aids]
    true_levels = [TRUTH_TO_ZH.get(key[aid]["quality_level"], key[aid]["quality_level"]) for aid in aids]
    scores = [eval_score.get(sid, float("nan")) for sid in sample_ids]

    rho, p = stats.spearmanr(mean_ordinal, scores)
    print("=== 评估分 vs 人工标注 相关（Spearman）===")
    print(f"  ρ = {rho:.3f}  (p = {p:.4f})")
    print(f"  说明：用每位标注员的档位均值(好=2/中=1/差=0) 与系统自动总分做秩相关\n")

    # 多数档位 vs 真实档位 的命中率（盲评有效性旁证）
    hit = sum(1 for m, t in zip(majority, true_levels) if m == t)
    print(f"  多数档位与真实档位命中率：{hit}/{len(aids)} = {hit/len(aids):.1%}")
    print("  （真实档位来自样本构造标签，标注员是盲评，命中率越高说明标准越清晰）\n")

    # 逐样本明细
    print("=== 逐样本明细 ===")
    print(f"{'匿名':<4} {'真实':<6} {'标注员':<8} {'多数档':<5} {'真实档':<6} {'总分':>5}")
    for i, aid in enumerate(aids):
        names = ",".join([f"{n}={v}" for (n, _), v in zip(annotators, ratings_matrix[i])])
        print(f"{aid:<5} {sample_ids[i]:<7} {names:<20} {majority[i]:<5} {true_levels[i]:<6} {scores[i]:>5}")

    out = {
        "n_raters": n_raters,
        "n_samples": len(aids),
        "fleiss_kappa": round(kappa, 3),
        "spearman_vs_eval_rho": round(float(rho), 3),
        "spearman_p": round(float(p), 4),
        "majority_vs_truth_hit_rate": round(hit / len(aids), 3),
        "per_sample": [
            {
                "anonymous_id": aid,
                "sample_id": sample_ids[i],
                "truth_level": true_levels[i],
                "ratings": ratings_matrix[i],
                "majority": majority[i],
                "eval_total": scores[i],
            }
            for i, aid in enumerate(aids)
        ],
    }
    out_path = ANNOTATION_DIR / "annotation_report.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已保存 → {out_path.name}")


if __name__ == "__main__":
    main()
