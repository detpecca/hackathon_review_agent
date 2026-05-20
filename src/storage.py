"""
MinIO 对象存储管理
- 作品文件上传/下载
- 评审报告存储
"""
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from src.config.settings import get_settings

_settings = get_settings()

_client = None


def get_minio_client() -> Minio:
    """获取MinIO客户端单例"""
    global _client
    if _client is None:
        _client = Minio(
            _settings.minio_endpoint,
            access_key=_settings.minio_access_key,
            secret_key=_settings.minio_secret_key,
            secure=_settings.minio_secure,
        )
    return _client


async def ensure_buckets():
    """确保所需bucket存在"""
    client = get_minio_client()
    buckets = [_settings.minio_bucket_submissions, _settings.minio_bucket_reports]
    for bucket in buckets:
        if not client.bucket_exists(bucket):
            try:
                client.make_bucket(bucket)
            except S3Error as e:
                if e.code != "BucketAlreadyOwnedByYou":
                    raise


async def upload_submission(submission_id: str, file_data: bytes, filename: str) -> str:
    """
    上传作品文件到MinIO
    返回对象存储路径
    """
    client = get_minio_client()
    object_name = f"{submission_id}/{filename}"

    client.put_object(
        bucket_name=_settings.minio_bucket_submissions,
        object_name=object_name,
        data=BytesIO(file_data),
        length=len(file_data),
    )
    return object_name


async def download_submission(object_path: str) -> bytes:
    """从MinIO下载作品文件"""
    client = get_minio_client()
    response = client.get_object(
        bucket_name=_settings.minio_bucket_submissions,
        object_name=object_path,
    )
    return response.read()


async def upload_report(submission_id: str, report_content: str) -> str:
    """上传评审报告"""
    client = get_minio_client()
    data = report_content.encode("utf-8")
    object_name = f"{submission_id}/report.md"

    client.put_object(
        bucket_name=_settings.minio_bucket_reports,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
    )
    return object_name


def get_submission_url(object_path: str, expiry: int = 3600) -> str:
    """获取作品文件的临时访问URL"""
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name=_settings.minio_bucket_submissions,
        object_name=object_path,
        expires=expiry,
    )
