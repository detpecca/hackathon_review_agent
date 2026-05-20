"""
人工复核路由（评委专用）
- 待复核列表
- 复核工作台材料
- 提交人工评分
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import FinalScore, Submission, DimensionScore, HumanReview
from src.schemas import HumanReviewInput, HumanReviewResult, ReviewMaterials

router = APIRouter(prefix="/human-reviews", tags=["Human Review"])


@router.get("/pending", summary="获取待人工复核作品列表")
async def list_pending_human_reviews(
    question_id: int = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取需要人工复核的作品列表:
    - Verifier置信度 < 0.8
    - 各维度评分方差 > 15
    - 功能测试失败但LLM评分 > 80
    """
    query = (
        select(Submission, FinalScore)
        .join(FinalScore, Submission.id == FinalScore.submission_id)
        .where(FinalScore.human_review_required == True)
        .where(FinalScore.human_reviewed == False)
        .order_by(desc(Submission.submitted_at))
    )

    if question_id:
        query = query.where(Submission.question_id == question_id)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    return {
        "total": len(rows),  # TODO: actual count
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "submission_id": str(sub.id),
                "team_id": str(sub.team_id),
                "question_id": sub.question_id,
                "total_score": fs.total_score,
                "confidence": fs.confidence,
                "human_review_reason": "Verifier confidence below threshold",
            }
            for sub, fs in rows
        ],
    }


@router.get("/{submission_id}/materials", summary="获取评委复核工作台材料")
async def get_review_materials(submission_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    返回评委复核所需的完整材料包:
    - 作品文件预览
    - README内容
    - 测试结果
    - Agent评分详情
    - Verifier验证结果
    - 沙箱执行日志
    - 关键代码片段
    """
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # 各维度评分
    result = await db.execute(
        select(DimensionScore).where(DimensionScore.submission_id == submission_id)
    )
    dim_scores = result.scalars().all()

    return {
        "submission_id": str(submission_id),
        "project_files": submission.project_metadata.get("file_list", []) if submission.project_metadata else [],
        "readme_content": submission.project_metadata.get("readme_preview", "") if submission.project_metadata else "",
        "test_results": {},  # TODO
        "agent_scores": [
            {
                "dimension": ds.dimension,
                "score": ds.score,
                "confidence": ds.confidence,
                "reasoning": ds.reasoning,
                "strengths": ds.strengths,
                "weaknesses": ds.weaknesses,
            }
            for ds in dim_scores
        ],
        "verification_results": [],  # TODO
        "sandbox_logs": [],  # TODO
        "code_preview": [],  # TODO
    }


@router.post("/{submission_id}", summary="提交人工复核评分")
async def submit_human_review(
    submission_id: UUID,
    data: HumanReviewInput,
    db: AsyncSession = Depends(get_db),
):
    """
    评委提交人工调整后的评分
    - 记录调整前后的分数
    - 记录调整理由
    - 重新计算总分
    - 标记为已复核
    """
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # 获取当前最终评分
    result = await db.execute(
        select(FinalScore).where(FinalScore.submission_id == submission_id)
    )
    final = result.scalar_one_or_none()
    if not final:
        raise HTTPException(status_code=400, detail="No final score found")

    original_total = final.total_score

    # 记录人工复核
    review = HumanReview(
        submission_id=submission_id,
        reviewer_name=data.reviewer_name,
        reviewed_dimensions=list(data.adjusted_scores.keys()),
        original_scores={
            "functionality": final.functionality_score,
            "code_quality": final.code_quality_score,
            "architecture": final.architecture_score,
            "innovation": final.innovation_score,
            "documentation": final.documentation_score,
            "testing": final.testing_score,
        },
        adjusted_scores=data.adjusted_scores,
        adjustment_reason=data.adjustment_reason or "",
    )
    db.add(review)

    # 更新最终评分
    if "functionality" in data.adjusted_scores:
        final.functionality_score = data.adjusted_scores["functionality"]
    if "code_quality" in data.adjusted_scores:
        final.code_quality_score = data.adjusted_scores["code_quality"]
    if "architecture" in data.adjusted_scores:
        final.architecture_score = data.adjusted_scores["architecture"]
    if "innovation" in data.adjusted_scores:
        final.innovation_score = data.adjusted_scores["innovation"]
    if "documentation" in data.adjusted_scores:
        final.documentation_score = data.adjusted_scores["documentation"]
    if "testing" in data.adjusted_scores:
        final.testing_score = data.adjusted_scores["testing"]

    # 获取赛题权重重新计算
    from src.models import Question
    q = await db.get(Question, submission.question_id)
    weights = q.evaluation_weights if q else {}

    # 重新计算加权总分
    total = 0
    if final.functionality_score and "functionality" in weights:
        total += final.functionality_score * weights["functionality"]
    if final.code_quality_score and "code_quality" in weights:
        total += final.code_quality_score * weights["code_quality"]
    if final.architecture_score and "architecture" in weights:
        total += final.architecture_score * weights["architecture"]
    if final.innovation_score and "innovation" in weights:
        total += final.innovation_score * weights["innovation"]
    if final.documentation_score and "documentation" in weights:
        total += final.documentation_score * weights["documentation"]
    if final.testing_score and "testing" in weights:
        total += final.testing_score * weights["testing"]

    final.total_score = round(total, 2)
    final.human_reviewed = True
    final.human_adjusted_score = final.total_score
    final.reviewer_notes = data.reviewer_notes or ""

    await db.commit()

    return {
        "submission_id": str(submission_id),
        "reviewer_name": data.reviewer_name,
        "original_total": original_total,
        "adjusted_total": final.total_score,
        "finalized": True,
    }
