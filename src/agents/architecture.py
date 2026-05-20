"""架构评审Agent"""
from typing import Dict, Any

from src.agents.base import BaseReviewAgent


class ArchitectureReviewAgent(BaseReviewAgent):
    template_name = "architecture_review.j2"
    dimension_name = "architecture"
    default_model = "gpt-4o"
    default_temperature = 0.3

    def review_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        context = self._build_context(state)
        return self.review_sync(context)

    def _build_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        files = state.get("parsed_files", {})
        deps = state.get("dependencies", {})

        key_modules = []
        for path, info in files.items():
            if any(k in path.lower() for k in ["main", "app", "core", "service", "controller"]):
                key_modules.append({
                    "name": path,
                    "purpose": f"{info.get('language', 'code')} module",
                    "dependencies": list(deps.get(path, [])),
                })

        return {
            "question_description": state.get("question_description", "N/A"),
            "file_tree": state.get("file_tree", ""),
            "dependencies": deps,
            "dependency_analysis": self._analyze_dependencies(deps),
            "key_modules": key_modules[:5],
        }

    def _analyze_dependencies(self, deps: Dict) -> str:
        if not deps:
            return "No explicit dependencies found."
        ext_libs = set()
        for dep_list in deps.values():
            for d in dep_list:
                if not d.startswith(".") and "/" not in d:
                    ext_libs.add(d)
        if ext_libs:
            return f"External libraries: {', '.join(sorted(ext_libs))}"
        return "Project uses standard library primarily."
