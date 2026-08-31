# FinInsight — 行业研报智能分析与问答系统

> **个人/活动作品，非腾讯官方发布。** 本项目为 2026 腾讯犀牛鸟开源人才计划实战任务作品。

基于 [Hy3](https://github.com/Tencent-Hunyuan/Hy3) 构建的金融研报结构化摘要生成器，配套多维度 Rubric 自动评估方法与有效性验证。

## 功能

- **结构化摘要生成**：输入研报 → 输出核心结论/关键数据/主要风险/投资建议/疑点，每条结论标注原文出处
- **交互式问答**：基于研报内容回答用户问题
- **多报告对比**：跨报告观点对比与矛盾检测
- **自动评估**：7 维度 Rubric 评测（事实准确性/证据可追溯性/数据精确性/信息完整性/结构规范性/安全合规性/专业术语正确性）

## 环境要求

- Python 3.11+
- Node.js 18+
- Hy3 API Key（通过 SiliconFlow/OpenRouter 等平台获取）

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/AmbientZw/FinInsight.git
cd FinInsight

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 HY3_API_KEY

# 3. 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. 启动前端
cd frontend
npm install
npm run dev
```

## 评测

```bash
# 运行完整评测
python evaluation/scripts/run_evaluation.py

# 运行有效性验证
python evaluation/validation/run_validation.py
```

## 免责声明

本系统输出仅供参考，不构成任何投资建议。投资有风险，决策需谨慎。所有分析结果应结合专业判断使用。

## 数据来源

评测样本来源于公开披露的上市公司年报及自行构造的模拟研报，仅用于学术研究和技术评估目的。

## License

Apache 2.0
