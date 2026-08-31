"""LLM-as-Judge prompt templates for D1, D2, D4, D7.

重要设计约束：TokenHub 的 Hy3 强制开启 thinking 模式，复杂评测任务（如"逐项核查"）
会触发 90s+ 的思考过程，导致服务器断连或 content 为空。因此所有 Judge prompt 都采用
"直接输出 JSON、不要求分析过程"的极简形式，将思考时间控制在 ~15s 内。
"""

# 统一输出 schema：{"score": int, "reasoning": str, "issues": [str]}
_UNIFIED_OUTPUT = """直接输出一个JSON对象，不要输出任何分析过程、解释或额外文字：
{"score": 5, "reasoning": "一句话评分理由", "issues": ["具体问题1"]}
其中 issues 列出发现的具体问题，无问题则为 []。"""

FACTUAL_ACCURACY_PROMPT = f"""你是一位资深金融评审员。对比「原始研报」与「AI摘要」，判断摘要中的事实（结论、数据、风险、建议）是否与原文一致。

评分（0-5分）：
5=所有事实与原文一致
4=仅单位/四舍五入等轻微偏差
3=1-2处非核心事实错误
2=多处数字或事实偏差
0=关键数据或结论与原文矛盾（如把盈利说成亏损）

{_UNIFIED_OUTPUT}"""

TRACEABILITY_PROMPT = f"""你是一位资深金融评审员。检查「AI摘要」中的每条关键结论是否标注了原文出处（页码或段落位置）。

评分（0-5分）：
5=每条关键结论均标注原文位置
4=大部分标注了出处，个别遗漏
3=约半数标注了出处
2=只有部分结论标注来源
0=关键结论无任何出处

{_UNIFIED_OUTPUT}"""

COMPLETENESS_PROMPT = f"""你是一位资深金融评审员。判断「AI摘要」是否遗漏了「原始研报」中的关键信息（核心结论、关键数据、主要风险、投资建议、需核实的疑点）。

评分（0-5分）：
5=核心结论/关键数据/风险/疑点无遗漏
4=覆盖绝大部分要点，极个别遗漏
3=覆盖主要要点但有遗漏
2=遗漏较多关键信息
0=漏掉原文核心结论或重大风险

{_UNIFIED_OUTPUT}"""

TERMINOLOGY_PROMPT = f"""你是一位资深金融评审员。检查「AI摘要」中的金融专业术语是否准确、是否存在误用导致含义偏差的情况（如把"摊薄"当"增厚"）。

评分（0-5分）：
5=术语准确且贴合语境
4=术语基本准确，极个别可优化
3=术语大体正确偶有不当
2=多处术语使用不当
0=误用术语导致含义相反

{_UNIFIED_OUTPUT}"""


def get_judge_user_prompt(source_text: str, output_text: str) -> str:
    return f"""## 原始研报
{source_text[:8000]}

## 待评审摘要
{output_text[:8000]}"""
