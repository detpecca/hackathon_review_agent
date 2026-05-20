"""
Celery 报告生成任务
- 汇总各Agent评审结果
- 生成Markdown格式的评审报告
- 上传到MinIO
"""
import logging

from src.celery_app import celery_app
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_review_report(self, submission_id: str):
    """
    生成完整评审报告

    Returns:
        {"submission_id": str, "report_path": str, "status": str}
    """
    logger.info(f"[Report:{self.request.id}] Generating report for {submission_id}")

    # TODO:
    # 1. 从数据库查询所有维度评分
    # 2. 查询Verifier结果
    # 3. 查询沙箱执行结果
    # 4. 使用Jinja2模板渲染Markdown报告
    # 5. 上传到MinIO

    report_content = f"""# 评审报告

> 作品ID: {submission_id}
> 生成时间: 2026-05-18

## 评分概览

| 维度 | 得分 | 置信度 |
|------|------|--------|
| 功能正确性 | - | - |
| 代码质量 | - | - |
| 架构设计 | - | - |
| 创新性 | - | - |

## 详细评审意见

(TODO: 由各Agent评审结果填充)

## 改进建议

1. ...
2. ...
3. ...

---
*本报告由AI评审系统自动生成，仅供参考。*
"""

    # TODO: await storage.upload_report(submission_id, report_content)
    return {
        "submission_id": submission_id,
        "report_path": f"{submission_id}/report.md",
        "status": "completed",
    }
