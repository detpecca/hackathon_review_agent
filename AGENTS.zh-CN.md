# AGENTS.zh-CN.md

供 AI 编码代理在本仓库中协作时参考的说明。

## 项目概览

本仓库实现了一个 AI 黑客松评审系统：

- `src/` 中的 FastAPI 后端
- 用于评审、沙箱执行和报告生成的 Celery workers
- 通过 Docker Compose 启动的 PostgreSQL、Redis、MinIO 和 Docker-in-Docker 服务
- `src/workflows/review_graph.py` 中基于 LangGraph 的评审流程
- `src/agents/` 中的 LLM 评审代理和 verifier 逻辑
- `frontend/` 中由 nginx 提供服务的静态前端
- `prompts/` 中的 prompt 模板
- `database/schema.sql` 中的数据库 schema

主要运行入口：

- 前端：`http://localhost:4399`
- API 文档：`http://localhost:8000/docs`
- API 健康检查：`http://localhost:8000/api/v1/health`
- MinIO 控制台：`http://localhost:9001`

## 仓库结构

- `src/main.py`：FastAPI 应用初始化和路由注册。
- `src/config/settings.py`：通过 `.env` 加载的 Pydantic 配置。
- `src/models.py`：SQLAlchemy ORM 模型。
- `src/schemas.py`：Pydantic 请求/响应 schema。
- `src/database.py`：数据库 engine/session 辅助函数。
- `src/storage.py`：MinIO bucket 和对象操作。
- `src/routers/`：API 路由模块。
- `src/agents/`：功能、代码质量、架构、创新和 verifier 评审代理。
- `src/workflows/`：LangGraph 评审编排。
- `src/tasks/`：Celery 任务入口。
- `src/sandbox/`：Docker 沙箱执行。
- `src/reports/`：评审报告生成。
- `src/cache/`：Redis 辅助函数。
- `frontend/`：原生 HTML/CSS/JS 管理界面。
- `docker/`：Docker Compose 和服务 Dockerfile。
- `database/schema.sql`：PostgreSQL schema 和种子数据。
- `api/openapi.yaml`：OpenAPI 契约。
- `tests/`：测试和注入式赛题 fixture。
- `test_project/`：示例提交项目。

## 环境准备

创建本地配置：

```bash
cp .env.example .env
```

安装本地开发依赖：

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

在 Windows PowerShell 中激活虚拟环境：

```powershell
.\venv\Scripts\Activate.ps1
```

## 常用命令

启动完整 Docker 服务栈：

```bash
cd docker
docker compose -p hackathon_review up -d
```

停止 Docker 服务栈：

```bash
cd docker
docker compose -p hackathon_review down
```

查看服务状态：

```bash
cd docker
docker compose -p hackathon_review ps
```

本地运行 API：

```bash
uvicorn src.main:app --reload --port 8000
```

本地运行 Celery worker：

```bash
celery -A src.celery_app worker -Q review,sandbox,report -l info
```

运行测试：

```bash
pytest
```

运行指定测试：

```bash
pytest tests/path/to_test.py -q
```

查看服务日志：

```bash
docker logs -f hackathon-api
docker logs -f hackathon-worker-review
docker logs -f hackathon-worker-sandbox
docker logs -f hackathon-worker-report
```

## 开发约定

- 新增抽象前，优先沿用 `src/routers`、`src/tasks`、`src/agents` 和 `src/workflows` 中已有模式。
- 修改路由契约时，同步保持 API 行为与 `api/openapi.yaml` 一致。
- 数据库变更需要同步更新 `src/models.py` 和 `database/schema.sql`。
- 请求/响应校验使用 `src/schemas.py` 中的 Pydantic schema。
- 配置统一从 `src/config/settings.py` 获取；不要在各模块中分散直接读取环境变量。
- 数据库访问保持 async SQLAlchemy 风格一致。
- 使用结构化 logging，避免使用 `print`。
- 较长的 prompt 文本放在 `prompts/*.j2` 中，不要硬编码在 Python 文件里。
- 沙箱执行必须保持隔离和资源限制。涉及 Docker socket 与用户提交代码路径时要特别谨慎。
- 不要提交密钥。`.env` 只用于本地；新增必需配置时同步更新 `.env.example`。

## 测试说明

- 路由、workflow、agent、沙箱执行、存储或评分逻辑发生行为变化时，应新增或更新测试。
- 单元测试中 mock LLM 调用。除非明确标记为 integration-only，否则避免依赖真实 API key。
- workflow 变更应尽量覆盖成功路径以及失败/重试状态。
- 沙箱变更需要验证超时、资源限制和不安全输入处理。
- 前端变更后，如果 Docker 正在运行，应手动检查 `http://localhost:4399`。

## LLM 评审系统说明

- 评审维度由专门的 agent 实现：
  - 功能完整性
  - 代码质量
  - 架构设计
  - 创新性
  - verifier 交叉检查
- Prompt 模板位于 `prompts/`；修改 agent 行为时，同步更新对应模板。
- `src/workflows/review_graph.py` 是 preprocess、sandbox test、review fan-out、verifier、decision 和 report generation 的协调入口。
- 分数结构和 JSON 解析应保持严格。LLM 输出格式错误时，应抛出带有有效上下文的错误。
- 不要假设只使用单一 LLM provider。配置中包含 OpenAI、Google 和 Qwen 相关字段。

## Docker 与沙箱说明

- 文档中常用的 Compose project name 是 `hackathon_review`。
- `docker/docker-compose.yml` 中固定了容器名，例如 `hackathon-api`、`hackathon-db`、`hackathon-redis` 和 `hackathon-minio`。
- 沙箱执行用户提交代码时会使用 Docker-in-Docker。相关改动可能影响宿主机安全和资源使用。
- 对权限、挂载卷、网络访问、CPU/内存限制和超时时间保持保守。
- 修改 worker queue 时，需要同时更新 Docker Compose command 和 Celery 任务路由。

## 前端说明

- 前端是 `frontend/` 下的原生 HTML/CSS/JS。
- nginx 负责提供静态 UI，并代理 API 请求。
- UI 变更应保持现有简洁管理台风格。
- 除非用户明确要求，或改动确实需要，否则不要引入构建系统。

## 编码说明

部分现有文档和注释在某些终端中可能显示为乱码。不要继续传播乱码文本。新文件应使用 UTF-8；除非明确需要中文文案，否则优先使用纯 ASCII。

