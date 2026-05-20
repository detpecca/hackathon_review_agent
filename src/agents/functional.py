"""功能评审Agent"""
from typing import Dict, Any

from src.agents.base import BaseReviewAgent


class FunctionalReviewAgent(BaseReviewAgent):
    template_name = "functional_review.j2"
    dimension_name = "functionality"
    default_model = "gpt-4o"
    default_temperature = 0.3

    def review_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """从工作流状态执行功能评审"""
        context = self._build_context(state)
        return self.review_sync(context)

    def _build_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "question_description": state.get("question_description", "N/A"),
            "baseline_description": state.get("baseline_description", "N/A"),
            "project_name": state.get("project_metadata", {}).get("name", "Unknown"),
            "primary_language": state.get("project_metadata", {}).get("language", "unknown"),
            "file_list": list(state.get("parsed_files", {}).keys()),
            "code_snippet": self._get_main_code(state),
            "test_results": state.get("test_results"),
            "build_status": state.get("build_status", "unknown"),
            "build_exit_code": state.get("build_exit_code", -1),
            "build_stderr": state.get("build_stderr", ""),
        }

    def _get_main_code(self, state: Dict[str, Any]) -> str:
        files = state.get("parsed_files", {})
        for path, info in files.items():
            if "main" in path.lower() or "app" in path.lower():
                return info.get("content_preview", "")[:3000]
        if files:
            first = list(files.values())[0]
            return first.get("content_preview", "")[:3000]
        return ""
