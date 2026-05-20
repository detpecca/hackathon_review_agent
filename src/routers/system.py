"""
系统管理路由
- 健康检查
- 任务统计
- 任务状态查询
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Submission, ReviewTask

router = APIRouter(prefix="", tags=["System"])


@router.get("/health", summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db)):
    """系统健康状态检查"""
    components = {
        "database": "ok",
        "redis": "ok",       # TODO: 实际检查
        "minio": "ok",       # TODO: 实际检查
        "sandbox_pool": "ok", # TODO: 实际检查
    }

    # 检查数据库
    try:
        await db.execute(select(func.count(Submission.id)))
    except Exception:
        components["database"] = "error"

    # 确定整体状态
    status = "ok" if all(v == "ok" for v in components.values()) else "degraded"

    from datetime import datetime, timezone
    return {
        "status": status,
        "version": "1.0.0",
        "components": components,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/tasks/stats", summary="评审任务队列统计")
async def get_task_stats(db: AsyncSession = Depends(get_db)):
    """获取评审任务队列的实时统计"""
    # 各状态统计
    result = await db.execute(
        select(ReviewTask.status, func.count(ReviewTask.id))
        .group_by(ReviewTask.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # 最近一小时完成/失败数
    from datetime import datetime, timedelta, timezone
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    completed_result = await db.execute(
        select(func.count(ReviewTask.id))
        .where(ReviewTask.status == "success")
        .where(ReviewTask.completed_at >= one_hour_ago)
    )
    completed_last_hour = completed_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(ReviewTask.id))
        .where(ReviewTask.status == "failure")
        .where(ReviewTask.completed_at >= one_hour_ago)
    )
    failed_last_hour = failed_result.scalar() or 0

    return {
        "pending": status_counts.get("pending", 0),
        "running": status_counts.get("running", 0),
        "completed_last_hour": completed_last_hour,
        "failed_last_hour": failed_last_hour,
        "avg_processing_time_ms": 0,  # TODO: 实际计算
        "queue_depth": status_counts.get("pending", 0) + status_counts.get("running", 0),
        "active_workers": 0,  # TODO: Celery监控
    }


@router.get("/tasks/{task_id}", summary="查询评审任务状态")
async def get_task_status(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """查询单个评审任务的详细状态"""
    task = await db.get(ReviewTask, task_id)
    if not task:
        return {"error": "Task not found"}

    return {
        "id": str(task.id),
        "submission_id": str(task.submission_id),
        "task_type": task.task_type,
        "status": task.status,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message,
    }
