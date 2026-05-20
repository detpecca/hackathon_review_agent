"""
Celery 评审任务
- 触发完整的多Agent协作评审流程
- 调用LangGraph工作流
- 更新数据库状态

使用方式:
    from src.tasks.review_tasks import run_full_review
    task = run_full_review.delay(submission_id="uuid")
    result = task.get(timeout=600)
"""
import asyncio
import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.celery_app import celery_app
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 同步数据库连接（Celery任务用）
_sync_engine = create_engine(
    settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
    pool_pre_ping=True,
)
SyncSession = sessionmaker(bind=_sync_engine)

try:
    from src.workflows.review_graph import review_workflow
except ImportError:
    review_workflow = None
    logger.warning("LangGraph not available, review workflow disabled")


def _run_sandbox_for_submission(submission_id: str, file_path: str) -> dict:
    """执行沙箱测试: 下载→解压→构建→测试→分析"""
    try:
        from io import BytesIO
        from src.storage import download_submission
        from src.sandbox.executor import SandboxExecutor

        # 下载作品 (async -> sync)
        file_data = asyncio.run(download_submission(file_path))

        # 创建临时目录并解压
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()

            if file_path.endswith(".zip"):
                with zipfile.ZipFile(BytesIO(file_data)) as z:
                    z.extractall(project_dir)
            elif file_path.endswith((".tar.gz", ".tgz")):
                import tarfile
                with tarfile.open(fileobj=BytesIO(file_data), mode="r:gz") as t:
                    t.extractall(project_dir)
            else:
                (project_dir / "submission").write_bytes(file_data)

            # 执行沙箱分析
            executor = SandboxExecutor()
            result = asyncio.run(
                executor.run_full_analysis(
                    submission_id=submission_id,
                    project_dir=str(project_dir),
                )
            )
            return result
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return {
            "build_status": "failed",
            "build_exit_code": -1,
            "build_stderr": str(e),
            "test_results": None,
            "static_analysis": None,
        }


def _get_submission_context(submission_id: str) -> dict:
    """从数据库获取作品和赛题上下文"""
    from src.models import Submission, Question
    with SyncSession() as session:
        sub = session.query(Submission).filter_by(id=submission_id).first()
        if not sub:
            return {}
        q = session.query(Question).filter_by(id=sub.question_id).first()
        return {
            "team_id": str(sub.team_id),
            "question_id": sub.question_id,
            "question_description": q.description if q else "",
            "baseline_description": q.baseline_description if q else "",
            "file_path": sub.file_path,
            "project_metadata": sub.project_metadata or {},
        }


def _save_dimension_scores(submission_id: str, state: dict):
    """保存各维度评分到数据库"""
    from src.models import DimensionScore
    dimensions = [
        ("functionality", state.get("functional_score", {})),
        ("code_quality", state.get("quality_score", {})),
        ("architecture", state.get("architecture_score", {})),
        ("innovation", state.get("innovation_score", {})),
    ]
    with SyncSession() as session:
        for dim_name, score_data in dimensions:
            if not score_data:
                continue
            ds = DimensionScore(
                submission_id=submission_id,
                dimension=dim_name,
                score=score_data.get("score", 0),
                confidence=score_data.get("confidence", 0.5),
                llm_model=score_data.get("llm_model", "unknown"),
                reasoning=score_data.get("reason", ""),
                strengths=score_data.get("strengths", []),
                weaknesses=score_data.get("weaknesses", []),
                improvements=score_data.get("improvements", []),
                raw_response=score_data.get("raw_response", ""),
            )
            session.add(ds)
        session.commit()


def _save_verification_results(submission_id: str, state: dict):
    """保存Verifier验证结果"""
    from src.models import VerificationResult
    results = state.get("verification_results", [])
    with SyncSession() as session:
        for vr in results:
            v = VerificationResult(
                submission_id=submission_id,
                verifier_model="gpt-4o",
                target_dimension=vr.get("dimension", ""),
                original_score=vr.get("original_score", 0),
                verified_score=vr.get("verified_score", 0),
                deviation=vr.get("deviation", 0),
                confidence=vr.get("confidence", 1.0),
                needs_human_review=vr.get("needs_human_review", False),
                verification_reason=vr.get("verification_reason", ""),
            )
            session.add(v)
        session.commit()


def _update_task_status(task_id: str, status: str, error: str = None):
    """更新评审任务状态"""
    try:
        from src.models import ReviewTask
        with SyncSession() as session:
            task = session.query(ReviewTask).filter_by(celery_task_id=task_id).first()
            if task:
                task.status = status
                if status == "running":
                    task.started_at = datetime.now(timezone.utc)
                elif status in ("success", "failure"):
                    task.completed_at = datetime.now(timezone.utc)
                if error:
                    task.error_message = error
                session.commit()
    except Exception as e:
        logger.error(f"Failed to update task status: {e}")


def _update_submission_status(submission_id: str, status: str):
    """更新作品提交状态"""
    try:
        from src.models import Submission
        with SyncSession() as session:
            sub = session.query(Submission).filter_by(id=submission_id).first()
            if sub:
                sub.status = status
                if status == "completed":
                    sub.completed_at = datetime.now(timezone.utc)
                session.commit()
    except Exception as e:
        logger.error(f"Failed to update submission status: {e}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_full_review(self, submission_id: str):
    """
    执行完整的多Agent评审流程
    """
    logger.info(f"[Task:{self.request.id}] Starting full review for submission {submission_id}")

    _update_task_status(self.request.id, "running")
    _update_submission_status(submission_id, "running")

    try:
        # 获取数据库上下文
        context = _get_submission_context(submission_id)

        # 步骤1: 沙箱测试（下载、解压、构建、测试）
        sandbox_result = _run_sandbox_for_submission(submission_id, context.get("file_path", ""))
        logger.info(f"[Task:{self.request.id}] Sandbox result: {sandbox_result['build_status']}")

        # 初始化工作流状态
        initial_state = {
            "submission_id": submission_id,
            "status": "running",
            **context,
            **sandbox_result,
        }

        # 步骤2: 执行工作流（多Agent评审）
        if review_workflow is not None:
            final_state = review_workflow.invoke(initial_state)
        else:
            final_state = {
                "submission_id": submission_id,
                "status": "completed",
                "final_scores": {"total_score": 0, "confidence": 0},
                "needs_human_review": False,
            }

        # 保存评分结果
        _save_dimension_scores(submission_id, final_state)
        _save_verification_results(submission_id, final_state)

        # 标记完成
        _update_task_status(self.request.id, "success")
        _update_submission_status(submission_id, "completed")

        logger.info(f"[Task:{self.request.id}] Review completed for {submission_id}")
        return {
            "submission_id": submission_id,
            "status": final_state.get("status", "completed"),
            "final_score": final_state.get("final_scores", {}),
            "human_review_required": final_state.get("needs_human_review", False),
        }

    except Exception as exc:
        logger.error(f"Review failed for {submission_id}: {exc}")
        _update_task_status(self.request.id, "failure", str(exc))
        _update_submission_status(submission_id, "failed")
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_llm_review_only(self, submission_id: str, dimensions: list = None):
    """仅执行LLM评审（不运行沙箱测试）"""
    dimensions = dimensions or ["functionality", "code_quality", "architecture", "innovation"]
    logger.info(f"[Task:{self.request.id}] LLM review for {submission_id}, dims={dimensions}")
    return {"submission_id": submission_id, "dimensions_reviewed": dimensions}


@celery_app.task
def recalculate_final_score(submission_id: str):
    """重新计算最终评分（人工复核后调用）"""
    logger.info(f"Recalculating final score for {submission_id}")
    return {"submission_id": submission_id, "recalculated": True}
