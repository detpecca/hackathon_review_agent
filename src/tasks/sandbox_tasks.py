"""
Celery 沙箱执行任务
- 在Docker容器中安全地构建和测试作品
- 采集静态分析结果
"""
import logging
import tempfile
from pathlib import Path

from src.celery_app import celery_app
from src.storage import download_submission
from src.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, time_limit=600)
def run_sandbox_tests(self, submission_id: str, file_path: str, language: str = None):
    """
    在沙箱中执行构建+测试+分析

    Args:
        submission_id: 作品ID
        file_path: MinIO中的对象路径
        language: 可选，指定语言（自动检测）

    Returns:
        dict: 沙箱执行结果
    """
    logger.info(f"[Sandbox:{self.request.id}] Testing submission {submission_id}")

    executor = SandboxExecutor()

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 从MinIO下载
        file_data = download_submission(file_path)

        # 解压
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()

        if file_path.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(BytesIO(file_data)) as z:
                z.extractall(project_dir)
        elif file_path.endswith((".tar.gz", ".tgz")):
            import tarfile
            with tarfile.open(fileobj=BytesIO(file_data), mode="r:gz") as t:
                t.extractall(project_dir)
        else:
            # 直接复制文件
            (project_dir / "submission").write_bytes(file_data)

        # 运行沙箱分析
        result = executor.run_full_analysis(
            submission_id=submission_id,
            project_dir=str(project_dir),
            language=language,
        )

    return {
        "submission_id": submission_id,
        **result,
    }


@celery_app.task(bind=True, max_retries=1, time_limit=600)
def run_injected_test_suite(self, submission_id: str, file_path: str, question_id: int):
    """
    注入赛题标准测试用例并执行
    用于验证作品是否满足赛题的核心功能要求
    """
    logger.info(f"[InjectedTests:{self.request.id}] Q{question_id} for {submission_id}")

    # TODO: 从数据库/question配置加载对应赛题的测试用例
    # test_code = load_question_tests(question_id)
    # result = executor.run_injected_tests(submission_id, project_dir, test_code, language)

    return {"submission_id": submission_id, "question_id": question_id, "status": "completed"}


from io import BytesIO
