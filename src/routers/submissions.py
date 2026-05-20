"""
作品提交路由（核心API）
- POST /submissions - 提交作品（Multipart上传）
- GET /submissions - 查询提交列表
- GET /submissions/{id} - 获取作品详情
- POST /submissions/{id}/retry - 重试评审
"""
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Submission, Question, Team, ReviewTask
from src.storage import upload_submission
from src.tasks.review_tasks import run_full_review

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/submissions", tags=["Submissions"])

# 允许的文件格式
ALLOWED_EXTENSIONS = {".zip", ".tar.gz", ".tgz"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="提交参赛作品",
    response_description="提交成功，返回提交信息和评审任务ID"
)
async def create_submission(
    team_id: UUID = Form(..., description="队伍ID"),
    question_id: int = Form(..., ge=1, le=7, description="赛题编号(1-7)"),
    file: UploadFile = File(..., description="作品ZIP/TAR.GZ文件"),
    description: Optional[str] = Form(None, description="作品说明"),
    db: AsyncSession = Depends(get_db),
):
    """
    提交参赛作品并自动触发评审流程:
    1. 校验文件格式和大小
    2. 校验队伍和赛题存在
    3. 计算版本号（同一队伍同一赛题多次提交）
    4. 上传文件到MinIO
    5. 创建数据库记录
    6. 触发Celery评审任务
    7. 返回提交信息和预估完成时间
    """
    # 校验文件扩展名
    filename = file.filename or "submission.zip"
    has_valid_ext = any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    if not has_valid_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 读取文件内容
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE // 1024 // 1024}MB",
        )

    # 校验队伍和赛题
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # 计算版本号
    result = await db.execute(
        select(func.max(Submission.submission_version))
        .where(
            Submission.team_id == team_id,
            Submission.question_id == question_id,
        )
    )
    max_version = result.scalar() or 0
    new_version = max_version + 1

    # 计算文件哈希
    file_hash = hashlib.sha256(file_content).hexdigest()

    # 上传到MinIO
    storage_path = await upload_submission(
        submission_id=str(team_id),  # 临时ID，会在创建记录后更新
        file_data=file_content,
        filename=filename,
    )

    # 创建数据库记录
    submission = Submission(
        team_id=team_id,
        question_id=question_id,
        submission_version=new_version,
        file_path=storage_path,
        file_size=len(file_content),
        file_hash=file_hash,
        metadata={
            "original_filename": filename,
            "description": description,
            "file_hash": file_hash,
        },
        status="pending",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 触发Celery评审任务（异步，不等待）
    task = run_full_review.delay(str(submission.id))

    # 创建任务追踪记录
    review_task = ReviewTask(
        submission_id=submission.id,
        celery_task_id=task.id,
        task_type="full_review",
        status="pending",
    )
    db.add(review_task)
    await db.commit()

    logger.info(f"Submission created: {submission.id} for team {team_id} Q{question_id}, task={task.id}")

    return {
        "id": str(submission.id),
        "team_id": str(team_id),
        "question_id": question_id,
        "submission_version": new_version,
        "file_path": storage_path,
        "file_size": len(file_content),
        "status": "pending",
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "review_task_id": str(review_task.id),
        "estimated_completion": None,  # TODO: 基于队列深度估算
    }


@router.get("", summary="查询作品提交列表")
async def list_submissions(
    team_id: Optional[UUID] = None,
    question_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    分页查询作品提交列表，支持按队伍、赛题、状态过滤
    """
    query = select(Submission)

    if team_id:
        query = query.where(Submission.team_id == team_id)
    if question_id:
        query = query.where(Submission.question_id == question_id)
    if status:
        query = query.where(Submission.status == status)

    # 总数
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # 分页
    query = query.order_by(Submission.submitted_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(s.id),
                "team_id": str(s.team_id),
                "question_id": s.question_id,
                "submission_version": s.submission_version,
                "file_size": s.file_size,
                "status": s.status,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in items
        ],
    }


@router.get("/{submission_id}", summary="获取作品详情及评审状态")
async def get_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    获取作品详情，包含评审进度和当前评分
    """
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # 加载关联数据
    await db.refresh(submission, ["dimension_scores", "final_score"])

    # 构建响应
    scores = None
    if submission.final_score:
        fs = submission.final_score
        scores = {
            "total_score": fs.total_score,
            "confidence": fs.confidence,
            "human_review_required": fs.human_review_required,
            "human_reviewed": fs.human_reviewed,
        }

    dimension_scores = []
    for ds in submission.dimension_scores:
        dimension_scores.append({
            "dimension": ds.dimension,
            "score": ds.score,
            "confidence": ds.confidence,
            "reasoning": ds.reasoning,
        })

    return {
        "id": str(submission.id),
        "team_id": str(submission.team_id),
        "question_id": submission.question_id,
        "submission_version": submission.submission_version,
        "file_size": submission.file_size,
        "file_hash": submission.file_hash,
        "status": submission.status,
        "metadata": submission.project_metadata,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "completed_at": submission.completed_at.isoformat() if submission.completed_at else None,
        "final_score": scores,
        "dimension_scores": dimension_scores,
    }


@router.post("/{submission_id}/retry", summary="重新触发评审")
async def retry_submission_review(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    重新触发评审流程（用于失败重试或手动重新评审）
    """
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # 重置状态
    submission.status = "pending"
    await db.commit()

    # 重新触发任务
    task = run_full_review.delay(str(submission_id))

    review_task = ReviewTask(
        submission_id=submission.id,
        celery_task_id=task.id,
        task_type="full_review",
        status="pending",
    )
    db.add(review_task)
    await db.commit()

    return {
        "submission_id": str(submission_id),
        "task_id": task.id,
        "status": "requeued",
    }
