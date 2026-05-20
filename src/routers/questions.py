"""
赛题管理路由
- 获取所有赛题列表
- 获取赛题详情
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Question

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("", summary="获取所有赛题")
async def list_questions(db: AsyncSession = Depends(get_db)):
    """获取全部7道赛题的基本信息"""
    result = await db.execute(select(Question).order_by(Question.id))
    questions = result.scalars().all()

    return [
        {
            "id": q.id,
            "question_code": q.question_code,
            "title": q.title,
            "max_score": q.max_score,
            "category": q.category,
            "evaluation_weights": q.evaluation_weights,
        }
        for q in questions
    ]


@router.get("/{question_id}", summary="获取赛题详情")
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    """获取赛题详细信息，包含描述和测试用例配置"""
    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": question.id,
        "question_code": question.question_code,
        "title": question.title,
        "description": question.description,
        "max_score": question.max_score,
        "category": question.category,
        "evaluation_weights": question.evaluation_weights,
        "baseline_description": question.baseline_description,
        "test_cases_config": question.test_cases_config,
    }
