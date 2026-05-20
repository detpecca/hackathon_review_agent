"""代码质量评审Agent"""
from typing import Dict, Any

from src.agents.base import BaseReviewAgent


class CodeQualityAgent(BaseReviewAgent):
    template_name = "code_quality_review.j2"
    dimension_name = "code_quality"
    default_model = "gpt-4o"
    default_temperature = 0.3

    def review_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        context = self._build_context(state)
        return self.review_sync(context)

    def _build_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        files = state.get("parsed_files", {})
        key_files = []
        for path, info in files.items():
            key_files.append({
                "path": path,
                "language": info.get("language", "text"),
                "content": info.get("content_preview", "")[:2000],
            })

        test_files = [p for p in files.keys() if "test" in p.lower()]
        total_loc = sum(
            len(info.get("content_preview", "").split("\n"))
            for info in files.values()
        )

        return {
            "question_description": state.get("question_description", "N/A"),
            "primary_language": state.get("project_metadata", {}).get("language", "unknown"),
            "file_count": len(files),
            "total_loc": total_loc,
            "test_files": test_files,
            "static_analysis": state.get("static_analysis") or {
                "lint_errors": 0,
                "lint_warnings": 0,
                "avg_complexity": 0,
                "max_complexity": 0,
                "duplication": 0,
                "security_issues": [],
                "dependency_vulns": [],
            },
            "file_tree": state.get("file_tree", ""),
            "key_files": key_files[:5],
        }
