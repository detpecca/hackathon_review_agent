-- ============================================================
-- AI Hackathon 2026 智能评审Agent系统 - 数据库Schema
-- 版本: V1.0
-- 说明: 完整DDL含表、索引、外键、触发器
-- ============================================================

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文检索支持

-- ============================================================
-- 1. 参赛队伍管理
-- ============================================================
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_code VARCHAR(20) UNIQUE NOT NULL,       -- 队伍编号如 T001
    team_name VARCHAR(100) NOT NULL,
    members JSONB,                                -- 队员信息数组
    contact_email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_teams_code ON teams(team_code);

-- ============================================================
-- 2. 赛题定义表
-- ============================================================
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    question_code VARCHAR(20) UNIQUE NOT NULL,   -- Q1~Q7
    title VARCHAR(200) NOT NULL,
    description TEXT,
    max_score INT NOT NULL DEFAULT 100,
    category VARCHAR(50) NOT NULL,               -- functional / agent / system
    evaluation_weights JSONB NOT NULL,            -- 各维度权重配置
    test_cases_config JSONB,                    -- 测试用例配置
    baseline_description TEXT,                   -- baseline方案描述（用于创新度对比）
    prompt_template_dir VARCHAR(100),            -- Prompt模板目录名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入7道赛题
INSERT INTO questions (question_code, title, description, max_score, category, evaluation_weights) VALUES
('Q1', '招投标信息聚合工具', '构建通用招投标信息聚合工具，验证搜索、抓取、聚合、展示等核心能力。任务目标是实现一个可运行的招投标信息聚合工具，形式为API/CLI/Web UI。', 150, 'functional', '{"functionality": 0.30, "code_quality": 0.20, "architecture": 0.15, "innovation": 0.15, "documentation": 0.10, "testing": 0.10}'),
('Q2', '文件整理助手', '设计并实现"文件整理助手"，帮助用户理解并整理已经高度杂乱的文件与目录集合。能在真实操作系统环境中运行，文件类型包括但不限于多媒体文件、文档、代码等。', 100, 'functional', '{"functionality": 0.30, "code_quality": 0.20, "architecture": 0.15, "innovation": 0.15, "documentation": 0.10, "testing": 0.10}'),
('Q3', '基于AI自动实现工业控制板嵌入式开发', '引入AI能力实现工业控制场景，不需要手写控制代码，构建一套AI Agent系统，完成温度传感器数据读取与三色灯状态控制。基于OpenClaw研发助手系统。', 200, 'agent', '{"functionality": 0.25, "code_quality": 0.20, "architecture": 0.20, "innovation": 0.20, "documentation": 0.10, "testing": 0.05}'),
('Q4', 'AI智能体记忆管理能力设计与评测', '探索和设计具备先进记忆管理能力的AI智能体系统，在给定算力和平台资源条件下，通过组织方统一指定的Benchmark进行评测。', 130, 'agent', '{"functionality": 0.20, "code_quality": 0.20, "architecture": 0.20, "innovation": 0.25, "documentation": 0.10, "testing": 0.05}'),
('Q5', 'PPT文档结构化检索与问答', '构建面向企业级PPT的"文档结构化检索与问答"原型系统，需支持PPT、PPTX、PDF等多种文档格式的统一接入与管理。', 100, 'functional', '{"functionality": 0.30, "code_quality": 0.20, "architecture": 0.15, "innovation": 0.15, "documentation": 0.10, "testing": 0.10}'),
('Q6', 'AI自动生成示意图（论文复现）', '面向企业应用场景的示意图生成工具，以用户提供的描述文字或文件为输入，能够输出矢量格式（可编辑）的示意图。', 200, 'system', '{"functionality": 0.15, "code_quality": 0.20, "architecture": 0.15, "innovation": 0.25, "documentation": 0.15, "testing": 0.10}'),
('Q7', 'Rust重构操作系统智能监控模块', '基于C语言操作系统监控组件源码，使用Rust进行完整重构，保留原有监控功能基础上提升安全性与健壮性，同时引入AI能力对监控数据进行智能分析。', 120, 'system', '{"functionality": 0.25, "code_quality": 0.25, "architecture": 0.20, "innovation": 0.15, "documentation": 0.10, "testing": 0.05}');

-- ============================================================
-- 3. 作品提交表
-- ============================================================
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    question_id INT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    submission_version INT NOT NULL DEFAULT 1,    -- 同一题多次提交版本号
    file_path VARCHAR(500) NOT NULL,              -- MinIO对象存储路径
    file_size BIGINT,                             -- 字节
    file_hash VARCHAR(64),                        -- SHA256校验
    metadata JSONB,                               -- 解析出的项目元数据
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/running/completed/failed
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(team_id, question_id, submission_version)
);

CREATE INDEX idx_submissions_team ON submissions(team_id);
CREATE INDEX idx_submissions_question ON submissions(question_id);
CREATE INDEX idx_submissions_status ON submissions(status);
CREATE INDEX idx_submissions_team_question ON submissions(team_id, question_id);

-- ============================================================
-- 4. 评审任务表（Celery任务追踪）
-- ============================================================
CREATE TABLE review_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    celery_task_id VARCHAR(100),
    task_type VARCHAR(50) NOT NULL,               -- full_review / sandbox_test / llm_review
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/running/success/failure/retry
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_review_tasks_submission ON review_tasks(submission_id);
CREATE INDEX idx_review_tasks_status ON review_tasks(status);

-- ============================================================
-- 5. 维度评分表（核心数据）
-- ============================================================
CREATE TABLE dimension_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    dimension VARCHAR(50) NOT NULL,               -- functionality/code_quality/architecture/innovation/documentation/testing
    score INT NOT NULL CHECK (score BETWEEN 0 AND 100),
    raw_score FLOAT,                             -- LLM输出的原始加权分
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1), -- 置信度
    verification_count INT DEFAULT 1,             -- 重复验证次数K
    llm_model VARCHAR(50),                        -- 使用的模型
    reasoning TEXT,                               -- 评分理由（LLM输出）
    strengths JSONB,                              -- 亮点数组
    weaknesses JSONB,                             -- 不足数组
    improvements JSONB,                           -- 改进建议数组
    raw_response JSONB,                           -- LLM原始JSON响应
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(submission_id, dimension)
);

CREATE INDEX idx_dim_scores_submission ON dimension_scores(submission_id);
CREATE INDEX idx_dim_scores_dimension ON dimension_scores(dimension);

-- ============================================================
-- 6. 交叉验证结果表（Verifier）
-- ============================================================
CREATE TABLE verification_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    verifier_model VARCHAR(50) NOT NULL,
    target_dimension VARCHAR(50) NOT NULL,         -- 被验证的维度
    original_score INT,                            -- 原始评分
    verified_score INT,                            -- 验证后评分
    deviation FLOAT,                               -- 偏差值
    confidence FLOAT,                             -- 验证置信度
    needs_human_review BOOLEAN DEFAULT FALSE,     -- 是否需人工复核
    verification_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(submission_id, target_dimension)
);

CREATE INDEX idx_verif_submission ON verification_results(submission_id);

-- ============================================================
-- 7. 最终评分汇总表
-- ============================================================
CREATE TABLE final_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
    functionality_score INT,
    code_quality_score INT,
    architecture_score INT,
    innovation_score INT,
    documentation_score INT,
    testing_score INT,
    test_execution_score INT,                     -- 自动化测试得分
    bonus_score INT DEFAULT 0,                   -- 额外加分
    total_score FLOAT NOT NULL,                   -- 加权总分
    confidence FLOAT,                             -- 整体置信度
    human_review_required BOOLEAN DEFAULT FALSE,  -- 是否需人工复核
    human_reviewed BOOLEAN DEFAULT FALSE,         -- 是否已人工复核
    human_adjusted_score FLOAT,                   -- 人工调整后分数
    reviewer_notes TEXT,                          -- 评委备注
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalized_at TIMESTAMP
);

CREATE INDEX idx_final_scores_total ON final_scores(total_score DESC);
CREATE INDEX idx_final_scores_human ON final_scores(human_review_required);

-- ============================================================
-- 8. 评审报告表
-- ============================================================
CREATE TABLE review_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    report_path VARCHAR(500),                     -- MinIO存储路径（Markdown/PDF）
    report_content TEXT,                          -- 报告文本内容（搜索用）
    summary TEXT,                                 -- 评审摘要
    generation_status VARCHAR(20) DEFAULT 'pending',
    generated_at TIMESTAMP,
    UNIQUE(submission_id)
);

CREATE INDEX idx_reports_submission ON review_reports(submission_id);

-- ============================================================
-- 9. 沙箱执行记录表
-- ============================================================
CREATE TABLE sandbox_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    container_id VARCHAR(100),
    image_used VARCHAR(100),
    execution_type VARCHAR(50),                   -- test / lint / build
    exit_code INT,
    stdout TEXT,
    stderr TEXT,
    execution_time_ms INT,
    resource_usage JSONB,                         -- {cpu_percent, memory_mb, disk_mb}
    security_flags JSONB,                         -- 安全检查标记
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sandbox_submission ON sandbox_executions(submission_id);

-- ============================================================
-- 10. 人工复核记录表
-- ============================================================
CREATE TABLE human_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    reviewer_name VARCHAR(100),
    reviewed_dimensions JSONB,                    -- 复核的维度
    original_scores JSONB,                        -- 原始分数
    adjusted_scores JSONB,                        -- 调整后分数
    adjustment_reason TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 11. 评分校准历史表（用于模型微调）
-- ============================================================
CREATE TABLE score_calibration_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    dimension VARCHAR(50),
    agent_score INT,
    human_score INT,
    delta INT,                                     -- 偏差
    prompt_version VARCHAR(20),                    -- 使用的Prompt版本
    model_version VARCHAR(50),                     -- 使用的模型版本
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 触发器: 自动更新 updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 触发器: 作品状态变更时记录日志
-- ============================================================
CREATE TABLE submission_status_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION log_submission_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO submission_status_logs (submission_id, old_status, new_status)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_status_change
AFTER UPDATE ON submissions
FOR EACH ROW EXECUTE FUNCTION log_submission_status_change();

-- ============================================================
-- 触发器: 最终评分自动计算（当维度评分更新时）
-- ============================================================
CREATE OR REPLACE FUNCTION recalculate_final_score()
RETURNS TRIGGER AS $$
DECLARE
    v_weights JSONB;
    v_question_id INT;
    v_total FLOAT := 0;
    v_weight_sum FLOAT := 0;
    v_confidence FLOAT := 0;
    v_dim_count INT := 0;
    v_rec RECORD;
BEGIN
    -- 获取赛题权重
    SELECT q.evaluation_weights, s.question_id INTO v_weights, v_question_id
    FROM submissions s JOIN questions q ON s.question_id = q.id
    WHERE s.id = NEW.submission_id;

    -- 计算加权分
    FOR v_rec IN
        SELECT dimension, score, confidence FROM dimension_scores
        WHERE submission_id = NEW.submission_id
    LOOP
        v_total := v_total + (v_rec.score * (v_weights->>v_rec.dimension)::FLOAT);
        v_weight_sum := v_weight_sum + (v_weights->>v_rec.dimension)::FLOAT;
        v_confidence := v_confidence + v_rec.confidence;
        v_dim_count := v_dim_count + 1;
    END LOOP;

    -- 更新或插入最终评分
    IF v_dim_count > 0 THEN
        INSERT INTO final_scores (
            submission_id, functionality_score, code_quality_score,
            architecture_score, innovation_score, documentation_score,
            testing_score, total_score, confidence
        )
        SELECT
            NEW.submission_id,
            MAX(CASE WHEN dimension='functionality' THEN score END),
            MAX(CASE WHEN dimension='code_quality' THEN score END),
            MAX(CASE WHEN dimension='architecture' THEN score END),
            MAX(CASE WHEN dimension='innovation' THEN score END),
            MAX(CASE WHEN dimension='documentation' THEN score END),
            MAX(CASE WHEN dimension='testing' THEN score END),
            v_total,
            v_confidence / v_dim_count
        FROM dimension_scores WHERE submission_id = NEW.submission_id
        ON CONFLICT (submission_id) DO UPDATE SET
            functionality_score = EXCLUDED.functionality_score,
            code_quality_score = EXCLUDED.code_quality_score,
            architecture_score = EXCLUDED.architecture_score,
            innovation_score = EXCLUDED.innovation_score,
            documentation_score = EXCLUDED.documentation_score,
            testing_score = EXCLUDED.testing_score,
            total_score = EXCLUDED.total_score,
            confidence = EXCLUDED.confidence,
            generated_at = CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_recalculate_final
AFTER INSERT OR UPDATE ON dimension_scores
FOR EACH ROW EXECUTE FUNCTION recalculate_final_score();

-- ============================================================
-- 视图: 排行榜
-- ============================================================
CREATE VIEW leaderboard AS
SELECT
    t.id AS team_id,
    t.team_code,
    t.team_name,
    q.question_code,
    q.title AS question_title,
    s.id AS submission_id,
    s.submission_version,
    s.status,
    fs.total_score,
    fs.confidence,
    fs.human_review_required,
    fs.human_reviewed,
    s.submitted_at,
    fs.generated_at AS scored_at
FROM teams t
JOIN submissions s ON t.id = s.team_id
JOIN questions q ON s.question_id = q.id
LEFT JOIN final_scores fs ON s.id = fs.submission_id
WHERE s.status = 'completed'
ORDER BY q.question_code, fs.total_score DESC;

-- ============================================================
-- 视图: 队伍总分榜
-- ============================================================
CREATE VIEW team_total_scores AS
SELECT
    t.id AS team_id,
    t.team_code,
    t.team_name,
    COUNT(DISTINCT s.question_id) AS questions_submitted,
    SUM(DISTINCT CASE WHEN fs.total_score IS NOT NULL THEN fs.total_score ELSE 0 END) AS total_score,
    AVG(fs.confidence) AS avg_confidence,
    SUM(CASE WHEN fs.human_review_required THEN 1 ELSE 0 END) AS pending_human_reviews
FROM teams t
LEFT JOIN submissions s ON t.id = s.team_id AND s.status = 'completed'
LEFT JOIN final_scores fs ON s.id = fs.submission_id
GROUP BY t.id, t.team_code, t.team_name
ORDER BY total_score DESC NULLS LAST;
