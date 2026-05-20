#!/bin/bash
# ============================================================
# AI Hackathon 评审系统 - 启动脚本
# 用法: ./start.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "Hackathon Review Agent 启动脚本"
echo "=================================="

# --- 1. 启动基础设施 ---
echo "[1/4] 启动基础设施 (DB/Redis/MinIO/DinD)..."
cd docker
docker compose up -d db redis minio dind

# 等待 healthy
echo "[2/4] 等待服务就绪..."
for svc in db redis minio dind; do
    until docker ps --format "{{.Names}}\t{{.Status}}" | grep "hackathon-$svc" | grep -q "healthy"; do
        echo "  等待 $svc ..."
        sleep 3
    done
done
echo "  基础设施全部就绪 ✓"

cd "$SCRIPT_DIR"

# --- 3. 构建镜像 (如需要) ---
echo "[3/4] 构建应用镜像..."
docker build -f docker/Dockerfile.api -t hackathon-api . && echo "  API 镜像 ✓"
docker build -f docker/Dockerfile.worker -t hackathon-worker . && echo "  Worker 镜像 ✓"

# --- 4. 启动 API 和 Worker ---
echo "[4/4] 启动 API 和 Worker..."

# 先清理旧容器
docker rm -f hackathon-api 2>/dev/null || true
docker rm -f hackathon-worker-review 2>/dev/null || true

# 启动 API
docker run -d --name hackathon-api \
  --network docker_hackathon-net \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://hackathon:hackathon_pass@db:5432/hackathon_db \
  -e REDIS_URL=redis://redis:6379/0 \
  -e MINIO_ENDPOINT=minio:9000 \
  -e MINIO_ACCESS_KEY=hackathon_minio \
  -e MINIO_SECRET_KEY=hackathon_minio_secret \
  -e CELERY_BROKER_URL=redis://redis:6379/1 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379/2 \
  hackathon-api && echo "  API 启动 ✓ (http://localhost:8000)"

# 启动 Worker
docker run -d --name hackathon-worker-review \
  --network docker_hackathon-net \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -e DATABASE_URL=postgresql://hackathon:hackathon_pass@db:5432/hackathon_db \
  -e REDIS_URL=redis://redis:6379/0 \
  -e MINIO_ENDPOINT=minio:9000 \
  -e MINIO_ACCESS_KEY=hackathon_minio \
  -e MINIO_SECRET_KEY=hackathon_minio_secret \
  -e CELERY_BROKER_URL=redis://redis:6379/1 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379/2 \
  -e OPENAI_API_KEY=sk-mock-key \
  hackathon-worker \
  celery -A src.celery_app worker -Q review -l info --concurrency=1 -n review@%h \
  && echo "  Worker 启动 ✓"

echo ""
echo "=================================="
echo "全部启动完成！"
echo "=================================="
echo "API 文档: http://localhost:8000/docs"
echo "健康检查: curl http://localhost:8000/api/v1/health"
echo ""
echo "常用命令:"
echo "  查看日志: docker logs -f hackathon-api"
echo "  查看Worker: docker logs -f hackathon-worker-review"
echo "  停止全部: docker rm -f hackathon-api hackathon-worker-review && cd docker && docker compose down"
