from openai import OpenAI

from app.config import settings

DISCLAIMER = (
    "⚠️ 免责声明：本分析由AI模型自动生成，仅供参考，不构成任何投资建议。"
    "投资有风险，决策需谨慎。请结合专业判断使用。"
)


class Hy3Client:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.hy3_api_key,
            base_url=settings.hy3_base_url,
            timeout=900.0,
        )
        self.model = settings.hy3_model

    def generate(
        self,
        messages: list[dict],
        reasoning_effort: str = "low",
        temperature: float = 0.7,
        max_tokens: int = 16000,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={
                "chat_template_kwargs": {"reasoning_effort": reasoning_effort}
            },
        )
        return response.choices[0].message.content

    def generate_stream(
        self,
        messages: list[dict],
        reasoning_effort: str = "low",
        temperature: float = 0.7,
        max_tokens: int = 16000,
    ):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            extra_body={
                "chat_template_kwargs": {"reasoning_effort": reasoning_effort}
            },
        )


hy3_client = Hy3Client()
