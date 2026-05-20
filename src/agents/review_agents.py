"""
5个专业评审Agent + Verifier交叉验证Agent 的具体实现
对应PRD Section 4.2 核心Agent模块
"""
import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseReviewAgent

logger = logging.getLogger(__name__)


# ============================================================
# 1. 功能评审Agent
# ============================================================
class FunctionalReviewAgent(BaseReviewAgent):
    """
    功能评审Agent
    - 评估功能完整性和正确性
    - 模型: GPT-4o (temp=0.3)
    - 权重: 核心功能40%, 边界条件25%, 错误处理20%, 输出格式15%
    """
    template_name = "functional_review.j2"
    dimension_name = "functionality"
    default_model = "gpt-4o"
    default_temperature = 0.3

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        # TODO: 从数据库/MinIO加载
        return {
            "project_name": kwargs.get("project_name", ""),
            "primary_language": kwargs.get("primary_language", "python"),
            "question_description": kwargs.get("question_description", ""),
            "baseline_description": kwargs.get("baseline_description", ""),
            "file_list": kwargs.get("file_list", []),
            "code_snippet": kwargs.get("code_snippet", ""),
            "test_results": kwargs.get("test_results", {}),
            "build_status": kwargs.get("build_status", "unknown"),
            "build_exit_code": kwargs.get("build_exit_code", -1),
            "build_stderr": kwargs.get("build_stderr", ""),
        }


# ============================================================
# 2. 代码质量Agent
# ============================================================
class CodeQualityAgent(BaseReviewAgent):
    """
    代码质量Agent
    - 评估代码质量、规范性和可维护性
    - 模型: Claude 3.5 Sonnet (temp=0.3)
    - 权重: 可读性20%, 测试覆盖20%, 安全性20%, 可维护性20%, 工程实践20%
    """
    template_name = "code_quality_review.j2"
    dimension_name = "code_quality"
    default_model = "gpt-4o"  # 可用 claude-3-5-sonnet 替换
    default_temperature = 0.3

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        return {
            "primary_language": kwargs.get("primary_language", "python"),
            "file_count": kwargs.get("file_count", 0),
            "total_loc": kwargs.get("total_loc", 0),
            "test_files": kwargs.get("test_files", []),
            "static_analysis": kwargs.get("static_analysis", {}),
            "file_tree": kwargs.get("file_tree", ""),
            "key_files": kwargs.get("key_files", []),
            "question_description": kwargs.get("question_description", ""),
        }


# ============================================================
# 3. 架构评审Agent
# ============================================================
class ArchitectureReviewAgent(BaseReviewAgent):
    """
    架构评审Agent
    - 评估系统架构设计和技术选型
    - 模型: GPT-4o (temp=0.3)
    - 权重: 模块化25%, 设计模式25%, 技术选型25%, 扩展性25%
    """
    template_name = "architecture_review.j2"
    dimension_name = "architecture"
    default_model = "gpt-4o"
    default_temperature = 0.3

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        return {
            "question_description": kwargs.get("question_description", ""),
            "file_tree": kwargs.get("file_tree", ""),
            "dependencies": kwargs.get("dependencies", {}),
            "dependency_analysis": kwargs.get("dependency_analysis", ""),
            "key_modules": kwargs.get("key_modules", []),
        }


# ============================================================
# 4. 创新性感知Agent
# ============================================================
class InnovationReviewAgent(BaseReviewAgent):
    """
    创新性感知Agent
    - 识别作品中的技术创新点和亮点
    - 模型: Qwen3-72B / DeepSeek-V3 (temp=0.5, 需要发散思维)
    - 权重: 相比baseline新颖性30%, 技术复杂度25%, 实际效果25%, 创造性20%
    """
    template_name = "innovation_review.j2"
    dimension_name = "innovation"
    default_model = "gpt-4o"  # 可用 qwen3-72b 或 deepseek-v3 替换
    default_temperature = 0.5  # 较高温度鼓励发散思维

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        return {
            "question_description": kwargs.get("question_description", ""),
            "baseline_description": kwargs.get("baseline_description", ""),
            "readme_content": kwargs.get("readme_content", ""),
            "innovative_snippets": kwargs.get("innovative_snippets", []),
            "approach_summary": kwargs.get("approach_summary", ""),
        }


# ============================================================
# 5. Verifier交叉验证Agent
# ============================================================
class VerifierCrossCheckAgent(BaseReviewAgent):
    """
    Verifier交叉验证Agent
    - 对其他Agent的评审结果进行独立验证
    - 对应PRD LLM-as-a-Verifier核心机制
    - 模型: Gemini 2.5 Flash (temp=0.2, 需要低温度保持客观)

    验证规则:
    1. 独立评估（不被告知原始评分）
    2. 偏差 >= 15分则标记人工复核
    3. 置信度 < 0.8 触发复核
    """
    template_name = "verifier_cross_check.j2"
    dimension_name = "verification"
    default_model = "gpt-4o"  # 可用 gemini-2.5-flash 替换
    default_temperature = 0.2  # 低温度保持客观

    # 偏差阈值
    DEVIATION_THRESHOLD = 15
    CONFIDENCE_THRESHOLD = 0.80

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        """
        构建Verifier上下文:
        - 原始评审结果
        - 作品摘要
        - 测试结果（作为ground truth）
        - 代码片段
        """
        return {
            "dimension": kwargs.get("dimension", ""),
            "original_reviewer_model": kwargs.get("original_reviewer_model", ""),
            "original_score": kwargs.get("original_score", 0),
            "original_reason": kwargs.get("original_reason", ""),
            "original_strengths": kwargs.get("original_strengths", []),
            "original_weaknesses": kwargs.get("original_weaknesses", []),
            "project_summary": kwargs.get("project_summary", ""),
            "test_results": kwargs.get("test_results", {}),
            "build_status": kwargs.get("build_status", ""),
            "lint_issues": kwargs.get("lint_issues", 0),
            "security_issues": kwargs.get("security_issues", 0),
            "language": kwargs.get("language", "python"),
            "code_under_review": kwargs.get("code_under_review", ""),
        }

    async def verify(
        self,
        submission_id: str,
        original_result: Dict[str, Any],
        context_builder: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        执行交叉验证

        Returns:
            {
                "original_score": int,
                "verified_score": int,
                "deviation": float,
                "confidence": float,
                "needs_human_review": bool,
                "verification_reason": str,
            }
        """
        # 构建Verifier专用上下文
        verify_context = {
            "dimension": original_result.get("dimension", ""),
            "original_reviewer_model": original_result.get("llm_model", ""),
            "original_score": original_result.get("score", 0),
            "original_reason": original_result.get("reason", ""),
            "original_strengths": original_result.get("strengths", []),
            "original_weaknesses": original_result.get("weaknesses", []),
            "project_summary": f"Submission {submission_id}",
            "code_under_review": original_result.get("code_snippet", ""),
        }

        # 调用Verifier评审
        verifier_result = await self.review(verify_context)

        verified_score = verifier_result.get("score", original_result["score"])
        original_score = original_result["score"]
        deviation = abs(verified_score - original_score)

        # 计算置信度（基于偏差）
        confidence = max(0.0, 1.0 - (deviation / 100.0))

        # 判定是否需要人工复核
        needs_human_review = (
            deviation >= self.DEVIATION_THRESHOLD
            or confidence < self.CONFIDENCE_THRESHOLD
        )

        result = {
            "original_score": original_score,
            "verified_score": verified_score,
            "deviation": deviation,
            "confidence": round(confidence, 4),
            "needs_human_review": needs_human_review,
            "verification_reason": verifier_result.get("reason", ""),
            "agree_with_original": "yes" if deviation < 5 else ("partial" if deviation < 15 else "no"),
            "key_disagreements": verifier_result.get("weaknesses", []),
            "verifier_model": self.default_model,
        }

        logger.info(
            f"Verification [{submission_id}/{original_result.get('dimension', '?')}]: "
            f"original={original_score}, verified={verified_score}, "
            f"deviation={deviation}, human_review={needs_human_review}"
        )
        return result


# ============================================================
# 6. 文档评审Agent（额外维度）
# ============================================================
class DocumentationReviewAgent(BaseReviewAgent):
    """
    文档评审Agent
    - 评估README、代码注释、使用说明的完整性
    - 可作为独立维度或融入其他Agent
    """
    template_name = "functional_review.j2"  # 复用模板，修改渲染上下文
    dimension_name = "documentation"
    default_model = "gpt-4o"
    default_temperature = 0.3

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        return {
            "question_description": kwargs.get("question_description", ""),
            "readme_content": kwargs.get("readme_content", ""),
            "has_api_doc": kwargs.get("has_api_doc", False),
            "has_tests": kwargs.get("has_tests", False),
            "comment_ratio": kwargs.get("comment_ratio", 0.0),
        }
