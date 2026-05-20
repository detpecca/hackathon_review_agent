"""
评分结果路由
- 各维度评分查询
- 评审报告下载
- 排行榜
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import DimensionScore, FinalScore, Submission, Team, Question, VerificationResult, SandboxExecution
from src.reports.generator import ReportGenerator

router = APIRouter(prefix="", tags=["Scores"])


@router.get("/submissions/{submission_id}/scores", summary="获取作品各维度评分")
async def get_dimension_scores(submission_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DimensionScore).where(DimensionScore.submission_id == submission_id)
    )
    scores = result.scalars().all()

    # 查询最终总分
    final_result = await db.execute(
        select(FinalScore).where(FinalScore.submission_id == submission_id)
    )
    final = final_result.scalar_one_or_none()

    return {
        "submission_id": str(submission_id),
        "scores": [
            {
                "dimension": s.dimension,
                "score": s.score,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
                "strengths": s.strengths,
                "weaknesses": s.weaknesses,
                "improvements": s.improvements,
                "llm_model": s.llm_model,
                "scored_at": s.scored_at.isoformat() if s.scored_at else None,
            }
            for s in scores
        ],
        "total_score": final.total_score if final else None,
        "overall_confidence": final.confidence if final else None,
    }


@router.get("/submissions/{submission_id}/verification", summary="获取Verifier交叉验证结果")
async def get_verification_results(submission_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取Verifier对各维度评分的交叉验证结果"""
    result = await db.execute(
        select(VerificationResult).where(VerificationResult.submission_id == submission_id)
    )
    verifications = result.scalars().all()

    return [
        {
            "id": str(v.id),
            "verifier_model": v.verifier_model,
            "target_dimension": v.target_dimension,
            "original_score": v.original_score,
            "verified_score": v.verified_score,
            "deviation": v.deviation,
            "confidence": v.confidence,
            "needs_human_review": v.needs_human_review,
            "verification_reason": v.verification_reason,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in verifications
    ]


@router.get("/submissions/{submission_id}/report", summary="获取评审报告")
async def get_review_report(
    submission_id: UUID,
    format: str = Query("markdown", enum=["markdown", "json"]),
    db: AsyncSession = Depends(get_db),
):
    """获取作品的完整评审报告（Markdown格式）"""
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # 获取队伍和赛题信息
    team = await db.get(Team, submission.team_id)
    question = await db.get(Question, submission.question_id)

    # 获取维度评分
    dim_result = await db.execute(
        select(DimensionScore).where(DimensionScore.submission_id == submission_id)
    )
    dim_scores = [
        {
            "dimension": ds.dimension,
            "score": ds.score,
            "confidence": ds.confidence,
            "llm_model": ds.llm_model,
            "reasoning": ds.reasoning,
            "strengths": ds.strengths or [],
            "weaknesses": ds.weaknesses or [],
            "improvements": ds.improvements or [],
        }
        for ds in dim_result.scalars().all()
    ]

    # 获取最终评分
    final_result = await db.execute(
        select(FinalScore).where(FinalScore.submission_id == submission_id)
    )
    final = final_result.scalar_one_or_none()
    final_score = {
        "total_score": final.total_score if final else None,
        "confidence": final.confidence if final else None,
        "human_review_required": final.human_review_required if final else False,
    } if final else None

    # 获取Verifier结果
    verif_result = await db.execute(
        select(VerificationResult).where(VerificationResult.submission_id == submission_id)
    )
    verifications = [
        {
            "dimension": v.target_dimension,
            "original_score": v.original_score,
            "verified_score": v.verified_score,
            "deviation": v.deviation,
        }
        for v in verif_result.scalars().all()
    ]

    # 获取沙箱结果
    sandbox_result = None
    sb_result = await db.execute(
        select(SandboxExecution)
        .where(SandboxExecution.submission_id == submission_id)
        .order_by(SandboxExecution.executed_at.desc())
    )
    sb = sb_result.scalar_one_or_none()
    if sb:
        sandbox_result = {
            "build_status": sb.build_status,
            "build_exit_code": sb.exit_code,
            "test_results": sb.stdout,
        }

    # 生成报告
    generator = ReportGenerator()
    report_md = generator.generate(
        submission_id=str(submission_id),
        team_name=team.team_name if team else "Unknown",
        question_title=question.title if question else "Unknown",
        dimension_scores=dim_scores,
        final_score=final_score,
        verification_results=verifications,
        sandbox_result=sandbox_result,
    )

    if format == "json":
        return {
            "submission_id": str(submission_id),
            "status": "completed",
            "content": report_md,
        }

    return {
        "submission_id": str(submission_id),
        "status": "completed",
        "content": report_md,
        "download_url": None,
    }


@router.get("/leaderboard", summary="获取排行榜")
async def get_leaderboard(
    question_id: int = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    排行榜: 按赛题或总分排序
    对应数据库视图: leaderboard, team_total_scores
    """
    if question_id:
        # 单赛题排行
        query = (
            select(
                Submission.id,
                Team.id.label("team_id"),
                Team.team_code,
                Team.team_name,
                FinalScore.total_score,
                FinalScore.confidence,
                FinalScore.human_reviewed,
            )
            .join(Team, Submission.team_id == Team.id)
            .join(FinalScore, Submission.id == FinalScore.submission_id)
            .where(Submission.question_id == question_id)
            .where(Submission.status == "completed")
            .order_by(desc(FinalScore.total_score))
        )

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        rows = result.all()

        # 获取赛题信息
        q = await db.get(Question, question_id)

        return {
            "question_id": question_id,
            "question_title": q.title if q else None,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "rank": idx + 1 + (page - 1) * page_size,
                    "team_id": str(r.team_id),
                    "team_code": r.team_code,
                    "team_name": r.team_name,
                    "total_score": r.total_score,
                    "confidence": r.confidence,
                    "human_reviewed": r.human_reviewed,
                }
                for idx, r in enumerate(rows)
            ],
        }
    else:
        # 总分榜
        from sqlalchemy.orm import aliased
        FS = aliased(FinalScore)
        SQ = aliased(Submission)

        # 使用team_total_scores视图逻辑
        result = await db.execute(
            select(
                Team.id,
                Team.team_code,
                Team.team_name,
                func.coalesce(func.sum(FinalScore.total_score), 0).label("total_score"),
                func.coalesce(func.avg(FinalScore.confidence), 0).label("avg_confidence"),
            )
            .outerjoin(Submission, Team.id == Submission.team_id)
            .outerjoin(FinalScore, Submission.id == FinalScore.submission_id)
            .where(Submission.status == "completed")
            .group_by(Team.id)
            .order_by(desc(func.sum(FinalScore.total_score)))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = result.all()

        return {
            "question_id": None,
            "question_title": "总分榜",
            "total": len(rows),  # TODO: 实际总数
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "rank": idx + 1 + (page - 1) * page_size,
                    "team_id": str(r.id),
                    "team_code": r.team_code,
                    "team_name": r.team_name,
                    "total_score": float(r.total_score) if r.total_score else 0,
                    "confidence": float(r.avg_confidence) if r.avg_confidence else 0,
                }
                for idx, r in enumerate(rows)
            ],
        }
