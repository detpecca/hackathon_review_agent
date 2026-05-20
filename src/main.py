"""
FastAPI 应用入口
- 路由注册
- 中间件
- 生命周期管理
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.config.settings import get_settings
from src.routers import teams, questions, submissions, scores, human_review, system

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动: 创建MinIO bucket（如果不存在）
    from src.storage import ensure_buckets
    await ensure_buckets()
    yield
    # 关闭: 清理资源


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI Hackathon 2026 智能评审Agent系统 API",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 路由注册
app.include_router(teams.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(human_review.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}", "version": "1.0.0"}
