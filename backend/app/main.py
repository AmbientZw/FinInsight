from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import reports, summary, qa, eval_routes

app = FastAPI(
    title="FinInsight API",
    description="行业研报智能分析与问答系统（个人/活动作品，非腾讯官方发布）",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(eval_routes.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
