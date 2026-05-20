"""Verifier交叉验证Agent"""
from typing import Dict, Any, List

from src.agents.base import BaseReviewAgent


class VerifierCrossCheckAgent(BaseReviewAgent):
    template_name = "verifier_cross_check.j2"
    dimension_name = "verifier"
    default_model = "gpt-4o"
    default_temperature = 0.2

    def verify_dimension(
        self,
        dimension: str,
        original_score: int,
        original_reason: str,
        original_strengths: List[str],
        original_weaknesses: List[str],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """对单个维度进行交叉验证"""
        context = {
            "dimension": dimension,
            "original_reviewer_model": state.get("original_reviewer_model", "gpt-4o"),
            "original_score": original_score,
            "original_reason": original_reason,
            "original_strengths": original_strengths or [],
            "original_weaknesses": original_weaknesses or [],
            "project_summary": self._build_project_summary(state),
            "test_results": state.get("test_results"),
            "build_status": state.get("build_status", "unknown"),
            "lint_issues": state.get("static_analysis", {}).get("lint_errors", 0),
            "security_issues": state.get("static_analysis", {}).get("security_issues", []),
            "language": state.get("project_metadata", {}).get("language", "python"),
            "code_under_review": self._get_sample_code(state),
        }
        return self.review_sync(context)

    def _build_project_summary(self, state: Dict[str, Any]) -> str:
        meta = state.get("project_metadata", {})
        files = state.get("parsed_files", {})
        return (
            f"Project: {meta.get('name', 'Unknown')}\n"
            f"Language: {meta.get('language', 'unknown')}\n"
            f"Files: {len(files)}\n"
            f"Build: {state.get('build_status', 'unknown')}"
        )

    def _get_sample_code(self, state: Dict[str, Any]) -> str:
        files = state.get("parsed_files", {})
        for path, info in files.items():
            content = info.get("content_preview", "")
            if len(content) > 50:
                return content[:2500]
        return ""
