"""Run full evaluation on sample set, output eval_table.csv.

支持断点续跑：已完成的样本（sample_id 已在 eval_table.csv 中）自动跳过。
单个 LLM 维度调用失败不会中断整体运行，会记为 3.0 分并标记待重试。
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))
load_dotenv(Path(__file__).resolve().parent.parent.parent / "backend" / ".env")

from evaluators.rules import (
    DataPrecisionEvaluator,
    StructureEvaluator,
    SafetyComplianceEvaluator,
)
from evaluators.llm_judge import (
    FactualAccuracyEvaluator,
    TraceabilityEvaluator,
    CompletenessEvaluator,
    TerminologyEvaluator,
)

WEIGHTS = {
    "事实准确性": 0.20,
    "证据可追溯性": 0.15,
    "数据精确性": 0.15,
    "信息完整性": 0.15,
    "结构规范性": 0.10,
    "安全合规性": 0.10,
    "专业术语正确性": 0.15,
}

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples" / "golden"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
CSV_PATH = RESULTS_DIR / "eval_table.csv"


def load_samples() -> list[dict]:
    samples_file = SAMPLES_DIR / "summary_samples.jsonl"
    if not samples_file.exists():
        print(f"样本文件不存在: {samples_file}")
        return []
    samples = []
    with open(samples_file) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def create_evaluators():
    api_key = os.environ.get("HY3_API_KEY", "")
    base_url = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    model = os.environ.get("HY3_MODEL", "hy3")

    rule_evaluators = [
        DataPrecisionEvaluator(),
        StructureEvaluator(),
        SafetyComplianceEvaluator(),
    ]

    llm_evaluators = [
        FactualAccuracyEvaluator(api_key, base_url, model),
        TraceabilityEvaluator(api_key, base_url, model),
        CompletenessEvaluator(api_key, base_url, model),
        TerminologyEvaluator(api_key, base_url, model),
    ]

    return rule_evaluators + llm_evaluators


def load_existing_results() -> tuple[list[dict], set[str]]:
    """返回 (已有结果行列表, 已完成 sample_id 集合)。"""
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        return df.to_dict("records"), set(df["sample_id"].astype(str))
    return [], set()


def save_results(results: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    json_path = RESULTS_DIR / "full_evaluation.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def evaluate_sample(sample: dict, evaluators) -> dict:
    source = sample.get("source_text", "")
    output = sample.get("output", "")
    row = {
        "sample_id": sample.get("sample_id", "unknown"),
        "quality_level": sample.get("quality_level", "unknown"),
        "difficulty": sample.get("difficulty", "unknown"),
    }
    failed_dims = []
    safety_red_flag = False

    for ev in evaluators:
        try:
            result = ev.evaluate(source, output)
        except Exception as e:  # noqa: BLE001
            from evaluators.base import EvalResult
            result = EvalResult(
                dimension=ev.dimension,
                score=3.0,
                reasoning=f"调用失败: {e}",
            )
            failed_dims.append(ev.dimension)

        row[result.dimension] = result.score
        row[f"{result.dimension}_reasoning"] = result.reasoning
        if result.dimension == "安全合规性" and result.score == 0:
            safety_red_flag = True

    weighted_sum = sum(row.get(dim, 0) * w for dim, w in WEIGHTS.items())
    row["总分"] = round(weighted_sum, 2)
    row["安全红线"] = safety_red_flag
    row["_failed_dims"] = ",".join(failed_dims)
    return row


def run():
    samples = load_samples()
    if not samples:
        print("没有找到评测样本，请先构建样本集。")
        return

    evaluators = create_evaluators()
    results, done_ids = load_existing_results()

    pending = [s for s in samples if s.get("sample_id") not in done_ids]
    if not pending:
        print(f"所有 {len(samples)} 个样本已完成，无需重复评测。")
        return
    print(f"已完成 {len(done_ids)}/{len(samples)}，待评测 {len(pending)} 个样本。")

    for i, sample in enumerate(pending, start=1):
        print(f"评测样本 {i}/{len(pending)}: {sample.get('sample_id', 'unknown')} "
              f"[{sample.get('quality_level', '')}]")
        row = evaluate_sample(sample, evaluators)
        results.append(row)
        # 每个样本完成后增量保存，避免网络中断丢失进度
        save_results(results)

    save_results(results)
    print(f"\n评测完成！结果已保存至: {CSV_PATH}")
    print(f"共评测 {len(results)} 个样本")

    failed = [r for r in results if r.get("_failed_dims")]
    if failed:
        print(f"\n⚠️ {len(failed)} 个样本存在调用失败维度（已按 3.0 分记录）：")
        for r in failed:
            print(f"  - {r['sample_id']}: {r['_failed_dims']}")
        print("可删除 CSV 中对应行后重新运行本脚本进行重试。")
    else:
        print("所有维度均成功评测，无失败。")


if __name__ == "__main__":
    run()
