"""有效性验证：判别力 / 一致性 / 对抗验证。

依赖 run_evaluation.py 生成的 results/eval_table.csv。
"""
import json
import os
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

DIMENSIONS = [
    "事实准确性", "证据可追溯性", "数据精确性",
    "信息完整性", "结构规范性", "安全合规性", "专业术语正确性",
]

# 质量等级 → 序数（用于秩相关）
LEVEL_ORDER = {"good": 2, "medium": 1, "bad": 0}


def load_eval_results() -> pd.DataFrame:
    csv_path = RESULTS_DIR / "eval_table.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"请先运行评测: {csv_path}")
    df = pd.read_csv(csv_path)
    # 新框架：硬门禁后的「封顶后总分」作为判别/秩相关/对抗的总分目标
    if "封顶后总分" in df.columns:
        df["总分"] = df["封顶后总分"]
    return df


def _cohens_d(a: pd.Series, b: pd.Series) -> float:
    """Cohen's d 效应量（good vs bad）。"""
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    na, nb = len(a), len(b)
    pooled = np.sqrt(
        ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    )
    if pooled == 0:
        return float("inf") if a.mean() != b.mean() else 0.0
    return (a.mean() - b.mean()) / pooled


def discrimination_validation(df: pd.DataFrame) -> dict:
    """5.1 判别力：三档 monotonic 排序 + Kruskal-Wallis + Cohen's d。"""
    results = {}
    for dim in DIMENSIONS + ["总分"]:
        if dim not in df.columns:
            continue

        groups = {}
        for level in ["good", "medium", "bad"]:
            subset = df[df["quality_level"] == level][dim].dropna()
            if len(subset) > 0:
                groups[level] = subset

        if len(groups) < 2:
            continue

        means = {k: round(float(v.mean()), 2) for k, v in groups.items()}
        monotonic = (
            means.get("good", -1) >= means.get("medium", -1) >= means.get("bad", -1)
        )

        h_stat = p_value = None
        group_values = list(groups.values())
        if len(group_values) >= 2 and all(len(g) >= 2 for g in group_values):
            try:
                h_stat, p_value = stats.kruskal(*group_values)
            except ValueError:
                pass

        d = _cohens_d(groups.get("good", pd.Series()), groups.get("bad", pd.Series())) \
            if "good" in groups and "bad" in groups else float("nan")

        results[dim] = {
            "means": means,
            "monotonic": bool(monotonic),
            "h_statistic": round(float(h_stat), 3) if h_stat is not None else None,
            "p_value": round(float(p_value), 4) if p_value is not None else None,
            "significant": bool(p_value is not None and p_value < 0.05),
            "cohens_d_good_vs_bad": round(float(d), 3) if not np.isnan(d) else None,
            "large_effect": bool(not np.isnan(d) and abs(d) > 0.8),
        }
    return results


def ground_truth_agreement(df: pd.DataFrame) -> dict:
    """与真实质量等级的秩相关（以 quality_level 为基准标注）。"""
    sub = df[df["quality_level"].isin(["good", "medium", "bad"])].copy()
    sub["level_rank"] = sub["quality_level"].map(LEVEL_ORDER)
    rho, p = stats.spearmanr(sub["level_rank"], sub["总分"])
    return {
        "spearman_rho": round(float(rho), 3),
        "p_value": round(float(p), 4),
        "significant": bool(p < 0.05),
    }


def consistency_validation(df: pd.DataFrame, n_samples: int = 10, n_runs: int = 3) -> dict:
    """5.2 一致性：同一样本重复评测稳定性（仅 LLM 维度；规则维度天然确定）。"""
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent / "backend" / ".env")

    from evaluators.llm_judge import (
        FactualAccuracyEvaluator,
        TraceabilityEvaluator,
        CompletenessEvaluator,
        TerminologyEvaluator,
    )

    api_key = os.environ.get("HY3_API_KEY", "")
    base_url = os.environ.get("HY3_BASE_URL", "")
    model = os.environ.get("HY3_MODEL", "hy3")
    evaluators = [
        FactualAccuracyEvaluator(api_key, base_url, model),
        TraceabilityEvaluator(api_key, base_url, model),
        CompletenessEvaluator(api_key, base_url, model),
        TerminologyEvaluator(api_key, base_url, model),
    ]

    samples_file = ROOT / "samples" / "golden" / "summary_samples.jsonl"
    samples = []
    with open(samples_file) as f:
        for line in f:
            samples.append(json.loads(line))

    # 平衡采样：尽量覆盖 good/medium/bad 三档
    levels = ["good", "medium", "bad"]
    by_level = {lv: [s for s in samples if s["quality_level"] == lv] for lv in levels}
    per_level = max(1, n_samples // len(levels))
    selected = []
    for lv in levels:
        selected.extend(by_level[lv][:per_level])
    if len(selected) < n_samples:
        selected.extend(by_level["good"][per_level: per_level + (n_samples - len(selected))])
    samples = selected[:n_samples]

    per_dim_std = {ev.dimension: [] for ev in evaluators}
    zero_var_counts = {ev.dimension: 0 for ev in evaluators}

    for s in samples:
        print(f"  一致性评测样本 {s['sample_id']}")
        for ev in evaluators:
            scores = []
            for _ in range(n_runs):
                try:
                    r = ev.evaluate(s["source_text"], s["output"])
                    scores.append(r.score)
                except Exception as e:  # noqa: BLE001
                    print(f"    [warn] {ev.dimension} 调用失败: {e}")
            if len(scores) >= 2:
                per_dim_std[ev.dimension].append(statistics.pstdev(scores))
                if all(x == scores[0] for x in scores):
                    zero_var_counts[ev.dimension] += 1

    dim_summary = {}
    for dim, stds in per_dim_std.items():
        dim_summary[dim] = {
            "avg_std": round(statistics.mean(stds), 3) if stds else None,
            "max_std": round(max(stds), 3) if stds else None,
            "zero_var_ratio": round(zero_var_counts[dim] / len(stds), 3) if stds else None,
        }

    return {
        "sample_count": len(samples),
        "runs_per_sample": n_runs,
        "dimensions": dim_summary,
        "note": "规则评测维度（数据精确性/结构规范性/安全合规性）为确定性算法，方差恒为 0",
    }


def adversarial_validation(df: pd.DataFrame) -> dict:
    """5.3 对抗验证：对抗样本不应被高估。"""
    adv = df[df["quality_level"].str.startswith("adversarial", na=False)].copy()
    if adv.empty:
        return {"note": "未找到对抗样本"}

    # 提取 report_id 与对抗类型
    adv["report_id"] = adv["sample_id"].str.split("_").str[0]
    adv["adv_type"] = adv["quality_level"].str.replace("adversarial_", "", regex=False)

    good = df[df["quality_level"] == "good"].copy()
    good["report_id"] = good["sample_id"].str.split("_").str[0]
    good_by_report = good.set_index("report_id")

    checks = []
    for _, row in adv.iterrows():
        base = good_by_report.loc[row["report_id"]]
        entry = {
            "sample_id": row["sample_id"],
            "adv_type": row["adv_type"],
            "adv_total": float(row["总分"]),
            "good_total": float(base["总分"]),
            "delta_total": round(float(row["总分"] - base["总分"]), 2),
        }

        # 类型专项检查
        if row["adv_type"] == "length_padding":
            entry["check"] = "D1事实准确性不应因注水而显著上升"
            entry["adv_D1"] = float(row.get("事实准确性", float("nan")))
            entry["good_D1"] = float(base.get("事实准确性", float("nan")))
            entry["passed"] = bool(row.get("事实准确性", 0) <= base.get("事实准确性", 0) + 1)
        elif row["adv_type"] == "jargon_stuffing":
            entry["check"] = "D7术语正确性不应高于原版"
            entry["adv_D7"] = float(row.get("专业术语正确性", float("nan")))
            entry["good_D7"] = float(base.get("专业术语正确性", float("nan")))
            entry["passed"] = bool(row.get("专业术语正确性", 0) <= base.get("专业术语正确性", 0))
        elif row["adv_type"] == "fake_citation":
            entry["check"] = "D1事实准确性应显著低于 good 基线（降幅 > 1 分）"
            entry["adv_D1"] = float(row.get("事实准确性", float("nan")))
            entry["good_D1"] = float(base.get("事实准确性", float("nan")))
            entry["passed"] = bool(row.get("事实准确性", 5) < base.get("事实准确性", 5) - 1)
        else:
            entry["check"] = "总分不应高于原版 good 样本"
            entry["passed"] = bool(row["总分"] <= base["总分"])

        checks.append(entry)

    total_passed = sum(1 for c in checks if c["passed"])
    return {
        "adversarial_count": len(adv),
        "total_passed": total_passed,
        "pass_rate": round(total_passed / len(adv), 3),
        "checks": checks,
    }


def _equivalence_variants(output_text: str) -> list[str]:
    """生成等价变形：list 条目重排 + 紧凑 JSON（空白变化）。"""
    try:
        data = json.loads(output_text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, dict):
        return []

    variants = []
    # 变形 1：每个 list 字段条目倒序
    reordered = {}
    for k, v in data.items():
        if isinstance(v, list) and len(v) > 1:
            reordered[k] = list(reversed(v))
        else:
            reordered[k] = v
    variants.append(json.dumps(reordered, ensure_ascii=False, indent=2))
    # 变形 2：紧凑 JSON（无缩进空白）
    variants.append(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return variants


def invariance_validation(n_samples: int = 5) -> dict:
    """5.4 等价不变性（IVR）：重排/空白变化不应改变规则维度分数。

    IVR 等价不变性：等价变形（不改变语义）应得到与原答案一致的分数。
    仅用规则维度（D3/D5/D6），零 API 成本。
    """
    from evaluators.rules import (
        DataPrecisionEvaluator,
        StructureEvaluator,
        SafetyComplianceEvaluator,
    )

    evaluators = [
        DataPrecisionEvaluator(),
        StructureEvaluator(),
        SafetyComplianceEvaluator(),
    ]

    samples_file = ROOT / "samples" / "golden" / "summary_samples.jsonl"
    samples = []
    with open(samples_file) as f:
        for line in f:
            s = json.loads(line)
            if s.get("quality_level") == "good":
                samples.append(s)
            if len(samples) >= n_samples:
                break

    violations = 0
    total_pairs = 0
    for s in samples:
        source = s["source_text"]
        base_scores = {ev.dimension: ev.evaluate(source, s["output"]).score for ev in evaluators}
        for variant in _equivalence_variants(s["output"]):
            v_scores = {ev.dimension: ev.evaluate(source, variant).score for ev in evaluators}
            for dim in base_scores:
                total_pairs += 1
                if abs(v_scores[dim] - base_scores[dim]) > 1e-6:
                    violations += 1

    return {
        "sample_count": len(samples),
        "variants_per_sample": 2,
        "total_pairs": total_pairs,
        "violations": violations,
        "ivr": round(violations / total_pairs, 6) if total_pairs else None,
    }


def run(skip_consistency: bool = False, consistency_samples: int = 10, n_runs: int = 3):
    df = load_eval_results()
    report = {}

    print("=== 5.1 判别力验证 ===")
    disc = discrimination_validation(df)
    report["discrimination"] = disc
    for dim, r in disc.items():
        mark = "✓" if (r["monotonic"] and r.get("significant")) else "✗"
        print(
            f"  {mark} {dim}: good={r['means'].get('good')} "
            f"medium={r['means'].get('medium')} bad={r['means'].get('bad')} "
            f"(p={r.get('p_value')}, d={r.get('cohens_d_good_vs_bad')})"
        )

    print("\n=== 与真实质量等级一致性 ===")
    agree = ground_truth_agreement(df)
    report["ground_truth_agreement"] = agree
    print(f"  Spearman rho={agree['spearman_rho']} (p={agree['p_value']})")

    if skip_consistency:
        print("\n=== 5.2 一致性验证（已跳过）===")
        report["consistency"] = {"note": "skipped"}
    else:
        print("\n=== 5.2 一致性验证（重复评测稳定性）===")
        cons = consistency_validation(df, n_samples=consistency_samples, n_runs=n_runs)
        report["consistency"] = cons
        for dim, r in cons["dimensions"].items():
            print(f"  {dim}: avg_std={r['avg_std']} max_std={r['max_std']} 零方差比例={r['zero_var_ratio']}")

    print("\n=== 5.3 对抗验证 ===")
    adv = adversarial_validation(df)
    report["adversarial"] = adv
    print(f"  对抗样本数: {adv.get('adversarial_count', 0)}, 通过率: {adv.get('pass_rate', 'N/A')}")
    for c in adv.get("checks", []):
        print(f"    {'✓' if c['passed'] else '✗'} {c['sample_id']} [{c['adv_type']}] {c['check']}")

    print("\n=== 5.4 等价不变性（IVR）===")
    inv = invariance_validation()
    report["invariance"] = inv
    print(f"  IVR = {inv['ivr']}（{inv['violations']}/{inv['total_pairs']} 对违反不变性）")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "validation_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n验证报告已保存至: {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-consistency", action="store_true", help="跳过重复评测稳定性验证（需调 API）")
    parser.add_argument("--consistency-samples", type=int, default=10)
    parser.add_argument("--n-runs", type=int, default=3)
    args = parser.parse_args()
    run(skip_consistency=args.skip_consistency,
        consistency_samples=args.consistency_samples,
        n_runs=args.n_runs)
