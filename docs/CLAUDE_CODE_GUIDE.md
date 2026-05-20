# Claude Code 分步操作指南

> 本指南详细说明如何将工程交付包交给 Claude Code，让它按步骤实现AI Hackathon 2026智能评审Agent系统。

---

## 第一步：准备环境

### 1.1 安装 Claude Code CLI

确保你已经在终端安装了 Claude Code：

```bash
# 安装 Claude Code（如果尚未安装）
npm install -g @anthropics/claude-code

# 验证安装
claude --version
```

### 1.2 创建工作目录

```bash
mkdir -p ~/hackathon-review-agent
cd ~/hackathon-review-agent
```

### 1.3 复制工程交付包

将 `hackathon_agent_project/` 目录下的所有文件复制到工作目录：

```bash
cp -r /path/to/hackathon_agent_project/* ~/hackathon-review-agent/
```

---

## 第二步：初始化工程（告诉 Claude Code 的第一件事）

### 2.1 启动 Claude Code

```bash
cd ~/hackathon-review-agent
claude
```

### 2.2 发送第一条指令

把下面这段完整复制粘贴给 Claude Code：

---

```
请你帮我实现一个AI编程大赛智能评审Agent系统。我已经准备好了完整的工程结构和所有必要文件。

**你先做以下准备工作：**

1. 阅读 `.env.example` 文件，复制为 `.env` 文件
2. 阅读 `docker/docker-compose.yml` 了解系统架构
3. 阅读 `database/schema.sql` 了解数据库表结构
4. 阅读 `api/openapi.yaml` 了解API接口定义
5. 阅读 `src/workflows/review_graph.py` 了解LangGraph工作流

**系统由以下核心模块组成：**
- FastAPI Web服务 (src/main.py)
- Celery任务队列 (src/celery_app.py)
- 5个AI评审Agent (src/agents/)
- Docker沙箱执行器 (src/sandbox/)
- PostgreSQL + Redis + MinIO 基础设施

请你先确认你理解了整个系统架构，然后告诉我接下来应该如何分阶段实现。
```

---

## 第三步：分阶段实现指令

### Phase 1：基础设施层（第1轮对话）

告诉 Claude Code：

---

```
**Phase 1：实现基础设施层**

请你实现以下模块，确保每个函数都有完整的实现（不是pass/TODO）：

1. **src/config/settings.py** - 已有完整实现，确认即可

2. **src/database.py** - 已有完整实现，确认即可

3. **src/storage.py** - 补充完整实现：
   - `ensure_buckets()` - 确保MinIO bucket存在
   - `upload_submission()` - 上传作品文件
   - `download_submission()` - 下载作品文件
   - `upload_report()` - 上传评审报告
   - 注意：函数签名已有，需要填充内部逻辑

4. **src/models.py** - 已有SQLAlchemy模型定义，确认关系正确

5. **src/celery_app.py** - Celery配置已有，确认即可

6. **创建 docker/.env 文件** 从 .env.example 复制

7. **验证 docker-compose.yml 可以启动**：
   ```bash
   docker-compose -f docker/docker-compose.yml up -d db redis minio
   ```

请先完成以上基础设施代码，然后告诉我Phase 1已完成。
```

---

### Phase 2：沙箱执行器（第2轮对话）

```
**Phase 2：实现Docker沙箱执行器**

请完整实现 `src/sandbox/executor.py` 中的所有TODO：

1. `run_full_analysis()` - 在Docker容器中执行构建+测试+分析
   - 使用docker-py库与Docker守护进程通信
   - 自动拉取所需的基础镜像
   - 限制容器资源（CPU/Memory/无网络）
   - 解析测试输出为结构化JSON

2. `run_injected_tests()` - 注入标准测试用例并执行
   - 从 `tests/fixtures/question_tests.py` 加载测试模板
   - 将测试代码写入作品目录
   - 执行并收集结果

3. 安全相关：
   - 确保 `--network none` 生效
   - seccomp配置文件
   - 敏感系统调用检查

4. 添加错误处理：
   - 镜像拉取失败的重试
   - 容器执行超时的处理
   - 日志过大时的截断

请先完成沙箱执行器，然后写一个简单测试验证它能正确运行Python项目的pytest。
```

---

### Phase 3：评审Agent引擎（第3轮对话）

```
**Phase 3：实现5个AI评审Agent + Verifier**

请完整实现 `src/agents/review_agents.py` 中的所有TODO：

1. **FunctionalReviewAgent** - 功能评审
   - 实现 `build_context()` - 从数据库加载作品信息和测试结果
   - 使用 GPT-4o (temperature=0.3)
   - Prompt模板: prompts/functional_review.j2

2. **CodeQualityAgent** - 代码质量评审
   - 实现 `build_context()` - 加载静态分析结果和代码度量
   - Prompt模板: prompts/code_quality_review.j2

3. **ArchitectureReviewAgent** - 架构评审
   - 实现 `build_context()` - 构建文件树和依赖分析
   - Prompt模板: prompts/architecture_review.j2

4. **InnovationReviewAgent** - 创新性感知
   - 实现 `build_context()` - 加载baseline对比材料
   - 使用 temperature=0.5（需要发散思维）
   - Prompt模板: prompts/innovation_review.j2

5. **VerifierCrossCheckAgent** - 交叉验证
   - 实现 `verify()` 方法
   - 偏差>=15分标记人工复核
   - 置信度<0.8标记人工复核
   - Prompt模板: prompts/verifier_cross_check.j2

6. **BaseReviewAgent** 基类补充：
   - `_get_system_prompt()` - 正确从Jinja2模板提取system prompt
   - `review_with_verification()` - K次重复验证逻辑

**技术要求：**
- 所有Agent必须输出严格JSON格式
- 评分必须是5的倍数（0-100）
- 每次评审记录到 dimension_scores 表
- LLM调用失败时优雅降级
```

---

### Phase 4：LangGraph工作流（第4轮对话）

```
**Phase 4：实现LangGraph评审工作流**

请完整实现 `src/workflows/review_graph.py` 中的所有TODO节点函数：

1. **preprocess_node()** - 预处理
   - 从MinIO下载作品ZIP
   - 解压并识别项目类型
   - 提取README、依赖文件、入口文件
   - 构建文件树和依赖图

2. **sandbox_test_node()** - 沙箱测试
   - 调用 SandboxExecutor.run_full_analysis()
   - 调用 SandboxExecutor.run_injected_tests()（注入赛题标准测试用例）
   - 收集测试结果和静态分析

3. **functional_review_node()** - 功能评审
   - 调用 FunctionalReviewAgent.review_with_verification(K=5)
   - 将结果写入 dimension_scores 表

4. **quality_review_node()** - 代码质量评审
   - 调用 CodeQualityAgent.review_with_verification(K=5)

5. **architecture_review_node()** - 架构评审
   - 调用 ArchitectureReviewAgent.review_with_verification(K=5)

6. **innovation_review_node()** - 创新评审
   - 调用 InnovationReviewAgent.review_with_verification(K=5)

7. **verifier_node()** - 交叉验证
   - 调用 VerifierCrossCheckAgent.verify() 对每个维度
   - 计算整体置信度
   - 判定是否需要人工复核

8. **decision_node()** - 决策
   - 按赛题权重计算加权总分
   - 判定最终路由（报告生成 或 人工复核标记）

9. **generate_report_node()** - 报告生成
   - 汇总所有评审结果
   - 使用Jinja2模板生成Markdown报告
   - 上传到MinIO

**工作流优化：**
- 四个评审Agent应真正并行执行（使用LangGraph的fan-out/fan-in）
- 添加超时控制（单节点5分钟）
- 添加错误恢复（单个Agent失败不影响整体）
```

---

### Phase 5：API路由层（第5轮对话）

```
**Phase 5：完整实现FastAPI路由**

已有骨架文件在 `src/routers/`，需要补充完整实现：

1. **src/routers/submissions.py** （核心）
   - `create_submission()` - 补充完整：
     * 文件格式校验（.zip/.tar.gz）
     * 文件大小限制（500MB）
     * SHA256哈希计算
     * 版本号自动递增
     * 触发Celery评审任务
     * 预估完成时间计算
   - `list_submissions()` - 分页+过滤
   - `get_submission()` - 包含评审进度
   - `retry_submission_review()` - 重试逻辑

2. **src/routers/teams.py** - 队伍注册和查询

3. **src/routers/scores.py** - 评分查询和排行榜
   - 单赛题排行榜
   - 队伍总分榜

4. **src/routers/human_review.py** - 人工复核工作台
   - 待复核列表（按置信度排序）
   - 复核材料包组装
   - 评分提交和重新计算

5. **src/routers/system.py** - 系统监控
   - 健康检查（实际检查各组件）
   - 任务队列统计

6. **src/main.py** - 注册所有路由，添加异常处理

**验证方式：**
```bash
# 启动服务
uvicorn src.main:app --reload

# 测试API
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/questions
```
```

---

### Phase 6：Celery任务集成（第6轮对话）

```
**Phase 6：完善Celery异步任务**

1. **src/tasks/review_tasks.py**
   - `run_full_review()` - 完整实现：
     * 调用LangGraph工作流
     * 超时控制（10分钟）
     * 失败重试（指数退避）
     * 进度状态更新到数据库
   - `run_llm_review_only()` - 仅LLM评审
   - `recalculate_final_score()` - 人工复核后重算

2. **src/tasks/sandbox_tasks.py**
   - `run_sandbox_tests()` - 完整实现
   - `run_injected_test_suite()` - 注入测试用例

3. **src/tasks/report_tasks.py**
   - `generate_review_report()` - 完整实现
   - 使用Jinja2模板生成美观的Markdown报告
   - 上传到MinIO

4. 确保任务序列化和反序列化正确
```

---

### Phase 7：集成测试（第7轮对话）

```
**Phase 7：端到端集成测试**

1. 创建 `tests/test_e2e.py`：
   - 模拟完整提交 -> 评审 -> 评分流程
   - 使用测试用的ZIP文件（创建一个简单的Python项目）

2. 创建 `tests/test_agents.py`：
   - 测试每个Agent的Prompt渲染
   - 测试JSON响应解析
   - 测试Verifier交叉验证

3. 创建 `tests/test_sandbox.py`：
   - 测试沙箱执行器
   - 测试安全限制（网络隔离等）

4. 验证完整流程：
```bash
# 1. 启动基础设施
docker-compose -f docker/docker-compose.yml up -d

# 2. 运行数据库迁移
# 使用 alembic 或手动执行 schema.sql

# 3. 启动API
uvicorn src.main:app --reload

# 4. 启动Celery Worker
celery -A src.celery_app worker -l info

# 5. 提交测试作品
curl -X POST "http://localhost:8000/api/v1/submissions" \
  -F "team_id=test-team-id" \
  -F "question_id=1" \
  -F "file=@test_project.zip"

# 6. 查询评审结果
curl "http://localhost:8000/api/v1/submissions/{id}/scores"
```

5. 修复发现的所有问题
```

---

## 第四步：Docker部署验证

```
**部署验证**

请确保所有服务可以通过docker-compose一键启动：

```bash
# 完整启动
docker-compose -f docker/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f api
docker-compose -f docker/docker-compose.yml logs -f celery-worker-review
docker-compose -f docker/docker-compose.yml logs -f celery-worker-sandbox

# 验证API
curl http://localhost:8000/api/v1/health
```
```

---

## 第五步：填充赛题数据

```
**最后一步：初始化大赛数据**

执行数据库初始化脚本填充7道赛题：

```bash
# 数据已在 schema.sql 末尾的 INSERT 语句中
# 确保questions表有7条记录
```

确认每道赛题都已配置：
- evaluation_weights（各维度权重）
- baseline_description（baseline方案描述，用于创新度对比）
- 测试用例模板（tests/fixtures/question_tests.py）
```

---

## 关键注意事项

### 每次对话的开场白模板

每次新对话时，先告诉Claude Code：

```
我们上一步完成了 [Phase X]。现在请进入 [Phase Y]。

**工程文件位置：** ~/hackathon-review-agent/
**关键文件：** [列出需要修改的文件]

请确保：
1. 所有TODO都被替换为实际实现
2. 每个函数有适当的错误处理
3. 使用已定义的Settings配置（不要硬编码）
4. 数据库操作使用async SQLAlchemy
5. LLM调用有重试机制和超时控制
```

### 常见问题处理

| 问题 | 解决方案 |
|------|----------|
| Claude Code 说文件太大 | 分文件发送，一次给2-3个 |
| Claude Code 遗漏了某些文件 | 明确列出文件路径让它读取 |
| 实现质量不高 | 明确要求"production-ready code" |
| 缺少错误处理 | 补充要求"add comprehensive error handling" |
| 测试不通过 | 给Claude Code看错误日志让它修复 |

### 代码质量要求

每次让Claude Code实现时，追加这段话：

```
代码质量要求：
- 所有函数必须有docstring
- 所有异步函数使用 async/await
- 数据库操作使用 async SQLAlchemy session
- 外部API调用有 @retry 装饰器
- 所有异常都被捕获并记录日志
- 不使用 print，统一使用 logging
- 配置项从Settings读取，禁止硬编码
```

---

## 交付物清单

完成所有Phase后，你将拥有：

| 模块 | 文件 | 状态 |
|------|------|------|
| 需求文档 | PRD PDF + HTML | 已完成 |
| 数据库Schema | database/schema.sql | Claude Code执行 |
| API定义 | api/openapi.yaml | 已完成 |
| Prompt模板 | prompts/*.j2 x5 | 已完成 |
| 基础设施 | docker-compose.yml | Claude Code执行 |
| FastAPI应用 | src/main.py | Claude Code实现 |
| 配置管理 | src/config/settings.py | 已完成 |
| 数据库模型 | src/models.py | 已完成 |
| 存储管理 | src/storage.py | Claude Code实现 |
| 工作流引擎 | src/workflows/review_graph.py | Claude Code实现 |
| 评审Agent | src/agents/*.py | Claude Code实现 |
| 沙箱执行器 | src/sandbox/executor.py | Claude Code实现 |
| API路由 | src/routers/*.py | Claude Code实现 |
| Celery任务 | src/tasks/*.py | Claude Code实现 |
| 测试用例 | tests/fixtures/*.py | 已完成 |
| 赛题数据 | schema.sql INSERT | 已完成 |

**总计：约 15+ 个文件需要Claude Code实现/补充**

---

## 时间估算

| Phase | 预估时间 | 依赖 |
|-------|---------|------|
| Phase 1: 基础设施 | 30分钟 | 无 |
| Phase 2: 沙箱执行器 | 45分钟 | Phase 1 |
| Phase 3: 评审Agent | 60分钟 | Phase 1 |
| Phase 4: LangGraph工作流 | 45分钟 | Phase 2,3 |
| Phase 5: API路由 | 60分钟 | Phase 1,3 |
| Phase 6: Celery任务 | 30分钟 | Phase 4,5 |
| Phase 7: 集成测试 | 45分钟 | Phase 6 |
| **总计** | **~6小时** | |

> 建议分3-4次会话完成，每次2-3个Phase。
