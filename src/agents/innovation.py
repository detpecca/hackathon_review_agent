"""创新性感知Agent"""
from typing import Dict, Any

from src.agents.base import BaseReviewAgent


class InnovationReviewAgent(BaseReviewAgent):
    template_name = "innovation_review.j2"
    dimension_name = "innovation"
    default_model = "gpt-4o"
    default_temperature = 0.5

    def review_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        context = self._build_context(state)
        return self.review_sync(context)

    def _build_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        files = state.get("parsed_files", {})
        snippets = []
        for path, info in files.items():
            content = info.get("content_preview", "")
            if len(content) > 100:
                snippets.append({
                    "language": info.get("language", "text"),
                    "code": content[:1500],
                })

        readme = ""
        for path, info in files.items():
            if "readme" in path.lower():
                readme = info.get("content_preview", "")
                break

        return {
            "question_description": state.get("question_description", "N/A"),
            "baseline_description": state.get("baseline_description", "N/A"),
            "readme_content": readme,
            "innovative_snippets": snippets[:3],
            "approach_summary": state.get("project_metadata", {}).get("description", "No description available."),
        }
