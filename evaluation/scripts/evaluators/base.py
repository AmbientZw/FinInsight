from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    dimension: str
    score: float
    max_score: float = 5.0
    reasoning: str = ""
    evidence: list[str] = field(default_factory=list)


class BaseEvaluator(ABC):
    dimension: str
    weight: float

    @abstractmethod
    def evaluate(
        self,
        source_text: str,
        output_text: str,
        reference: dict | None = None,
    ) -> EvalResult:
        pass


class RuleBasedEvaluator(BaseEvaluator):
    """Rule-based evaluator that doesn't need LLM calls."""
    pass


class LLMJudgeEvaluator(BaseEvaluator):
    """LLM-as-Judge evaluator that uses Hy3 for scoring."""

    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _judge(self, system_prompt: str, user_prompt: str) -> str:
        import time

        last_error = None
        # hy4-preview 强制 thinking（reasoning ~8000 token），需足够大的 max_tokens 才能返回 content
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=10000,
                    timeout=300.0,
                )
                return response.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001
                last_error = e
                time.sleep(3)
        raise RuntimeError(f"Judge 调用失败（3 次重试）: {last_error}")
