"""评分服务：复用 evaluation 模块的 7 维评测器，对生成的摘要进行混合评分。

仅用于测试/演示阶段，用于在页面上展示「评分过程」。通过 sys.path 引入
evaluation/scripts 下的评测器，与评测脚本共享同一套实现，避免评分口径不一致。
"""
import json
import sys
from pathlib import Path

from app.config import settings
from app.core.schemas import StructuredSummary

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVAL_SCRIPTS = _REPO_ROOT / "evaluation" / "scripts"
if str(_EVAL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_EVAL_SCRIPTS))

WEIGHTS = {
    "事实准确性": 0.20,
    "证据可追溯性": 0.15,
    "数据精确性": 0.15,
    "信息完整性": 0.15,
    "结构规范性": 0.10,
    "安全合规性": 0.10,
    "专业术语正确性": 0.15,
}


def _output_text(summary: StructuredSummary) -> str:
    return json.dumps(summary.model_dump(), ensure_ascii=False, indent=2)


def evaluate_summary_stream(report_text: str, summary: StructuredSummary):
    """逐个维度评测并流式产出结果（规则维度即时、LLM 维度逐个返回）。"""
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
    from evaluators.base import EvalResult
    from evaluators.hard_gate import apply_hard_gates

    output = _output_text(summary)
    llm_cfg = dict(
        api_key=settings.hy3_api_key,
        base_url=settings.hy3_base_url,
        model=settings.hy3_model,
    )

    evaluators = [
        DataPrecisionEvaluator(),
        StructureEvaluator(),
        SafetyComplianceEvaluator(),
        FactualAccuracyEvaluator(**llm_cfg),
        TraceabilityEvaluator(**llm_cfg),
        CompletenessEvaluator(**llm_cfg),
        TerminologyEvaluator(**llm_cfg),
    ]

    dims = []
    safety_red_flag = False
    for ev in evaluators:
        try:
            r = ev.evaluate(report_text, output)
        except Exception as e:  # noqa: BLE001
            r = EvalResult(dimension=ev.dimension, score=3.0, reasoning=f"调用失败: {e}")
        entry = {
            "dimension": r.dimension,
            "weight": WEIGHTS.get(r.dimension, 0.0),
            "score": r.score,
            "reasoning": r.reasoning,
            "evidence": r.evidence or [],
        }
        dims.append(entry)
        if r.dimension == "安全合规性" and r.score == 0:
            safety_red_flag = True
        yield entry

    weighted_total = round(sum(d["score"] * d["weight"] for d in dims), 2)
    dim_scores = {d["dimension"]: d["score"] for d in dims}
    total, gates = apply_hard_gates(weighted_total, dim_scores)
    yield {
        "done": True,
        "total": total,
        "weighted_total": weighted_total,
        "max_total": 5.0,
        "safety_red_flag": safety_red_flag or any(g["red_flag"] for g in gates),
        "hard_gates": gates,
    }
