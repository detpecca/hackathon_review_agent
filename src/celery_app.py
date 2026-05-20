"""
Celery 应用配置
- Broker: Redis (队列)
- Backend: Redis (结果)
- 路由: review队列(智能评审) / sandbox队列(沙箱执行) / report队列(报告生成)
"""
from celery import Celery
from src.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "hackathon_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.review_tasks",
        "src.tasks.sandbox_tasks",
        "src.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务路由
    task_routes={
        "src.tasks.review_tasks.*": {"queue": "review"},
        "src.tasks.sandbox_tasks.*": {"queue": "sandbox"},
        "src.tasks.report_tasks.*": {"queue": "report"},
    },

    # 重试策略
    task_default_retry_delay=60,
    task_max_retries=3,
    task_ack_late=True,
    worker_prefetch_multiplier=1,

    # 结果过期
    result_expires=3600 * 24 * 7,  # 7天

    # 监控
    worker_send_task_events=True,
    task_send_sent_event=True,
)
