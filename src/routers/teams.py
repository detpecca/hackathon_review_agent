"""
队伍管理路由
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Team, Submission
from src.schemas import TeamCreate, TeamResponse, PaginatedTeams

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="注册参赛队伍", response_model=TeamResponse)
async def create_team(data: TeamCreate, db: AsyncSession = Depends(get_db)):
    # 检查team_code是否已存在
    result = await db.execute(select(Team).where(Team.team_code == data.team_code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Team code already exists")

    team = Team(
        team_code=data.team_code,
        team_name=data.team_name,
        members=[m.model_dump() for m in data.members] if data.members else None,
        contact_email=str(data.contact_email) if data.contact_email else None,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("", summary="获取队伍列表")
async def list_teams(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)):
    query = select(Team).order_by(Team.created_at.desc())
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {"id": str(t.id), "team_code": t.team_code, "team_name": t.team_name,
             "contact_email": t.contact_email} for t in items
        ],
    }


@router.get("/{team_id}", summary="获取队伍详情及提交记录")
async def get_team(team_id: UUID, db: AsyncSession = Depends(get_db)):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # 加载提交记录
    result = await db.execute(select(Submission).where(Submission.team_id == team_id))
    submissions = result.scalars().all()

    return {
        "id": str(team.id),
        "team_code": team.team_code,
        "team_name": team.team_name,
        "members": team.members,
        "contact_email": team.contact_email,
        "created_at": team.created_at.isoformat() if team.created_at else None,
        "submissions": [
            {"id": str(s.id), "question_id": s.question_id, "version": s.submission_version,
             "status": s.status} for s in submissions
        ],
    }
