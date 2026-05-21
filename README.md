# AI Hackathon 智能评审Agent系统

基于多Agent协作的编程大赛作品自动评审系统。使用 LangGraph 编排评审工作流，4个专业化Agent并行评审 + Verifier交叉验证，支持人工复核兜底。

## 功能特性

- **多Agent并行评审**：Functionality / Code Quality / Architecture / Innovation 四个维度独立评分
- **Verifier交叉验证**：K次重复验证 + 置信度阈值过滤，低置信度自动触发人工复核
- **Docker沙箱执行**：隔离环境运行作品，自动测试功能正确性
- **LangGraph工作流编排**：DAG可视化评审流程，支持状态追踪和断点重试
- **人工复核工作台**：评委可查看完整评审材料，调整评分并记录理由
- **实时排行榜**：按赛题动态排名，支持分数明细穿透
- **前端管理后台**：纯HTML/CSS/JS，简洁GitHub风格设计

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐
│   前端 SPA   │────▶│  nginx      │────▶│      FastAPI 服务            │
│  (localhost:4399)  │     │  (反向代理)  │     │      (localhost:8000)        │
└─────────────┘     └─────────────┘     └──────────────┬──────────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                              ▼                        ▼                        ▼
                        ┌─────────┐            ┌──────────┐           ┌──────────────┐
                        │ PostgreSQL│            │  Redis   │           │   MinIO      │
                        │  (数据)   │            │(缓存/队列)│           │ (对象存储)    │
                        └─────────┘            └──────────┘           └──────────────┘
                                                       │
                                                       ▼
                                               ┌──────────────┐
                                               │ Celery Worker │
                                               │  - review     │
                                               │  - sandbox    │
                                               │  - report     │
                                               └──────┬───────┘
                                                      │
                                               ┌──────┴──────┐
                                               │ Docker沙箱   │
                                               │ (作品执行)   │
                                               └─────────────┘
```

### LangGraph 评审工作流

```
预处理 ──▶ 沙箱测试 ──┬──▶ 功能评审Agent ──┐
                      ├──▶ 代码质量Agent ──┼──▶ Verifier交叉验证 ──▶ 决策 ──▶ 报告生成
                      ├──▶ 架构评审Agent ──┤         │
                      └──▶ 创新评审Agent ──┘         ▼
                                              低置信度 ──▶ 人工复核队列
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Web框架 | FastAPI + Uvicorn |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2 (async) |
| 缓存/队列 | Redis 7 + Celery |
| 对象存储 | MinIO |
| AI/LLM | OpenAI GPT-4o / Google Gemini 2.5 Flash / Qwen3-72B |
| 工作流引擎 | LangGraph (DAG编排) |
| 前端 | Vanilla JS + HTML5 + CSS3 (nginx) |
| 容器化 | Docker + Docker Compose |
| 沙箱执行 | Docker-in-Docker |

## 快速开始

### 前置要求

- Docker Desktop (Windows/Mac) 或 Docker Engine + Docker Compose (Linux)
- Git

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd hackathon_review_agent
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

需要配置的关键变量：

```env
# LLM API Keys（至少配一个）
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-google-key

# 其他保持默认值即可
```

### 3. 启动全部服务

```bash
cd docker
docker compose -p hackathon_review up -d
```

等待约 30 秒让基础设施就绪，然后访问：

| 服务 | 地址 |
|------|------|
| 前端管理后台 | http://localhost:4399 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |
| MinIO 控制台 | http://localhost:9001 |

### 4. 验证运行状态

```bash
docker compose -p hackathon_review ps

# 测试 API
curl http://localhost:4399/api/v1/health
```

### 5. 停止服务

```bash
docker compose -p hackathon_review down
```

## 项目结构

```
.
├── src/                          # 后端源码
│   ├── main.py                   # FastAPI 入口
│   ├── config/settings.py        # 配置管理
│   ├── models.py                 # SQLAlchemy ORM 模型
│   ├── schemas.py                # Pydantic 数据校验
│   ├── routers/                  # API 路由 (6个模块)
│   ├── agents/                   # LLM 评审Agent (5个)
│   │   ├── base.py               # BaseReviewAgent 基类
│   │   ├── functional.py         # 功能评审Agent
│   │   ├── quality.py            # 代码质量Agent
│   │   ├── architecture.py       # 架构评审Agent
│   │   ├── innovation.py         # 创新评审Agent
│   │   └── verifier.py           # 交叉验证Agent
│   ├── workflows/review_graph.py # LangGraph DAG 定义
│   ├── tasks/                    # Celery 后台任务
│   ├── sandbox/executor.py       # Docker 沙箱执行器
│   ├── reports/generator.py      # Markdown 报告生成
│   └── cache/redis_client.py     # Redis 缓存
├── frontend/                     # 前端 SPA
│   ├── index.html                # 页面骨架
│   ├── app.js                    # 路由 + API + 渲染
│   ├── style.css                 # GitHub风格样式
│   ├── Dockerfile                # nginx 镜像
│   └── nginx.conf                # 静态文件 + API代理
├── docker/                       # Docker 配置
│   ├── docker-compose.yml        # 全栈编排
│   ├── Dockerfile.api            # API服务镜像
│   └── Dockerfile.worker         # Worker镜像
├── database/schema.sql           # PostgreSQL 初始化脚本
├── prompts/                      # LLM Prompt 模板 (Jinja2)
├── api/openapi.yaml              # OpenAPI 规范
├── tests/                        # 测试用例
├── .env.example                  # 环境变量模板
└── start.sh                      # 一键启动脚本
```

## 核心 API

所有接口前缀 `/api/v1`。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/teams` | CRUD | 队伍管理 |
| `/questions` | CRUD | 赛题管理 |
| `/submissions` | POST | 提交作品（自动触发评审） |
| `/submissions/{id}` | GET | 作品详情 |
| `/submissions/{id}/scores` | GET | 各维度分数 + 总分 |
| `/submissions/{id}/report` | GET | 评审报告 |
| `/scores/leaderboard` | GET | 排行榜 |
| `/human-reviews/pending` | GET | 待人工复核列表 |
| `/human-reviews/{id}` | POST | 提交人工评分 |

完整 API 文档见 http://localhost:8000/docs

## 评审维度与权重

系统从 6 个维度评分，权重由赛题配置：

| 维度 | 说明 | 默认权重 |
|------|------|---------|
| Functionality | 功能完整性与正确性 | 25% |
| Code Quality | 代码规范与可读性 | 20% |
| Architecture | 架构设计与扩展性 | 20% |
| Innovation | 创新性与技术亮点 | 15% |
| Documentation | 文档完整性 | 10% |
| Testing | 测试覆盖度 | 10% |

## 配置说明

### 环境变量

详见 `.env.example`。核心变量：

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 是（或配其他LLM）|
| `GOOGLE_API_KEY` | Google Gemini Key | 可选 |
| `DATABASE_URL` | PostgreSQL 连接串 | 否（有默认值）|
| `REDIS_URL` | Redis 连接串 | 否（有默认值）|
| `VERIFIER_K` | Verifier重复验证次数 | 否（默认5）|
| `CONFIDENCE_THRESHOLD` | 置信度阈值 | 否（默认0.8）|

### 沙箱配置

```env
SANDBOX_CPU_LIMIT=1.0          # 容器CPU限制
SANDBOX_MEMORY_LIMIT=512m      # 容器内存限制
SANDBOX_TIMEOUT=300            # 执行超时(秒)
SANDBOX_MAX_CONCURRENT=5       # 最大并发沙箱数
```

## 开发指南

### 本地开发（不依赖Docker）

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 PostgreSQL 和 Redis（需自行安装）

# 4. 配置 .env

# 5. 启动 API
uvicorn src.main:app --reload --port 8000

# 6. 启动 Worker（另开终端）
celery -A src.celery_app worker -Q review,sandbox,report -l info
```

### 添加新的评审维度

1. 在 `src/agents/` 下创建新的 Agent 类，继承 `BaseReviewAgent`
2. 在 `prompts/` 下添加对应的 prompt 模板
3. 在 `src/workflows/review_graph.py` 的 DAG 中加入新节点
4. 在 `src/models.py` 的 `FinalScore` 中添加新字段
5. 更新 `database/schema.sql` 中的触发器函数

### 日志查看

```bash
# API 日志
docker logs -f hackathon-api

# Worker 日志
docker logs -f hackathon-worker-review

# 沙箱执行日志
docker logs -f hackathon-worker-sandbox
```

## 常见问题

**Q: 沙箱执行失败？**  
A: 检查 `dind` 容器是否 healthy，`docker logs hackathon-dind` 查看 Docker daemon 日志。

**Q: API 返回 500？**  
A: 检查数据库连接：`docker logs hackathon-api | grep -i error`

**Q: 评审任务没有执行？**  
A: 检查 Worker 是否运行：`docker compose -p hackathon_review ps`，确认 Redis 队列有任务：`docker exec hackathon-redis redis-cli llen celery`。

## License

MIT
