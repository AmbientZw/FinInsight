"""LLM-as-Judge evaluators for D1, D2, D4, D7."""

import json
import statistics

from .base import LLMJudgeEvaluator, EvalResult
from .judge_prompts import (
    FACTUAL_ACCURACY_PROMPT,
    TRACEABILITY_PROMPT,
    COMPLETENESS_PROMPT,
    TERMINOLOGY_PROMPT,
    get_judge_user_prompt,
)

# 每个维度重复评测次数。1 = 快速跑通；3 = 取中位数（更稳定但更慢）
N_RUNS = 1


def _parse_unified(raw: str) -> dict:
    """解析统一 schema: {score, reasoning, issues}，带正则兜底。"""
    import re

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        # 截取第一个 JSON 对象，避免模型附带额外文字
        start = cleaned.find("{")
        if start >= 0:
            cleaned = cleaned[start:]
        data = json.loads(cleaned)
        score = max(0.0, min(5.0, float(data.get("score", 3.0))))
        return {
            "score": score,
            "reasoning": data.get("reasoning", ""),
            "issues": data.get("issues", []) or [],
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # 正则兜底：从任意文本中提取 score 字段
        m = re.search(r'"score"\s*:\s*([0-5](?:\.\d+)?)', raw)
        if m:
            return {
                "score": max(0.0, min(5.0, float(m.group(1)))),
                "reasoning": raw[:200],
                "issues": [],
            }
        return {"score": 3.0, "reasoning": "JSON解析失败", "issues": []}


class _JudgeEvaluatorBase(LLMJudgeEvaluator):
    """公共实现：不同维度仅 prompt 与名称不同。"""

    system_prompt: str = ""

    def evaluate(self, source_text: str, output_text: str, reference=None) -> EvalResult:
        scores = []
        last_reasoning = ""
        last_issues = []

        for _ in range(N_RUNS):
            raw = self._judge(
                self.system_prompt, get_judge_user_prompt(source_text, output_text)
            )
            parsed = _parse_unified(raw)
            scores.append(parsed["score"])
            last_reasoning = parsed["reasoning"]
            last_issues = parsed["issues"]

        return EvalResult(
            dimension=self.dimension,
            score=statistics.median(scores),
            reasoning=last_reasoning,
            evidence=last_issues,
        )


class FactualAccuracyEvaluator(_JudgeEvaluatorBase):
    """D1: Factual accuracy of the summary against source."""

    dimension = "事实准确性"
    weight = 0.20
    system_prompt = FACTUAL_ACCURACY_PROMPT


class TraceabilityEvaluator(_JudgeEvaluatorBase):
    """D2: Whether conclusions cite source locations."""

    dimension = "证据可追溯性"
    weight = 0.15
    system_prompt = TRACEABILITY_PROMPT


class CompletenessEvaluator(_JudgeEvaluatorBase):
    """D4: Information completeness of the summary."""

    dimension = "信息完整性"
    weight = 0.15
    system_prompt = COMPLETENESS_PROMPT


class TerminologyEvaluator(_JudgeEvaluatorBase):
    """D7: Professional terminology correctness."""

    dimension = "专业术语正确性"
    weight = 0.15
    system_prompt = TERMINOLOGY_PROMPT
