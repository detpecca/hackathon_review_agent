"""
沙箱执行器 (subprocess-based, 绕过 docker-py 兼容性问题)
- Docker容器隔离执行
- 支持多语言项目构建和测试
"""
import json
import logging
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LANGUAGE_IMAGES = {
    "python": "python:3.11-slim",
    "javascript": "node:20-slim",
    "typescript": "node:20-slim",
    "java": "openjdk:17-slim",
    "rust": "rust:1.75-slim",
    "go": "golang:1.21",
    "unknown": "python:3.11-slim",
}

TEST_COMMANDS = {
    "python": {
        "install": "pip install -r requirements.txt",
        "test": "pytest --tb=short -q --json-report --json-report-file=/tmp/test_results.json || true",
        "lint": "pylint --output-format=json *.py src/ > /tmp/lint.json 2>/dev/null || true",
        "build": "python -m py_compile $(find . -name '*.py' | head -20)",
    },
    "javascript": {
        "install": "npm install",
        "test": "npm test -- --json --outputFile=/tmp/test_results.json || true",
        "lint": "npx eslint . -f json > /tmp/lint.json 2>/dev/null || true",
        "build": "npm run build || true",
    },
}


def _docker_cmd(args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """执行docker CLI命令"""
    cmd = ["docker"] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


class SandboxExecutor:
    def __init__(self):
        self.cpu_limit = settings.sandbox_cpu_limit
        self.memory_limit = settings.sandbox_memory_limit
        self.timeout = settings.sandbox_timeout

    def detect_language(self, project_dir: str) -> str:
        path = Path(project_dir)
        files = [f.name for f in path.iterdir() if f.is_file()]

        if "Cargo.toml" in files:
            return "rust"
        elif "package.json" in files:
            return "typescript" if "tsconfig.json" in files else "javascript"
        elif any(f in files for f in ["requirements.txt", "pyproject.toml", "setup.py"]):
            return "python"
        elif any(f in files for f in ["pom.xml", "build.gradle"]):
            return "java"
        elif "go.mod" in files:
            return "go"

        exts = {}
        for f in path.rglob("*"):
            if f.is_file() and f.suffix:
                exts[f.suffix] = exts.get(f.suffix, 0) + 1
        ext_to_lang = {".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java", ".rs": "rust", ".go": "go"}
        if exts:
            return ext_to_lang.get(max(exts, key=exts.get), "unknown")
        return "unknown"

    def _build_run_script(self, language: str) -> str:
        cmds = TEST_COMMANDS.get(language, TEST_COMMANDS["python"])
        script = "#!/bin/bash\ncd /workspace\n\necho '=== BUILD ==='\n"
        # install 步骤容错（requirements.txt 等可能不存在）
        if cmds.get("install"):
            script += f"({cmds['install']}) || true\n"
        if cmds.get("build"):
            script += f"({cmds['build']}) || true\n"
        script += "\necho '=== TEST ==='\n"
        if cmds.get("test"):
            script += f"{cmds['test']}\n"
        script += "\necho '=== LINT ==='\n"
        if cmds.get("lint"):
            script += f"({cmds['lint']}) || true\n"
        script += "\necho '=== DONE ==='\n"
        return script

    async def run_full_analysis(
        self,
        submission_id: str,
        project_dir: str,
        language: Optional[str] = None,
    ) -> Dict:
        if language is None:
            language = self.detect_language(project_dir)

        image = LANGUAGE_IMAGES.get(language, LANGUAGE_IMAGES["unknown"])
        run_script = self._build_run_script(language)
        work_dir = Path(project_dir).resolve()

        logger.info(f"[Sandbox:{submission_id}] Running {language} analysis in {image}")

        # 确保镜像存在
        pull_result = _docker_cmd(["pull", image], timeout=300)
        if pull_result.returncode != 0:
            logger.warning(f"Pull image failed: {pull_result.stderr}")

        # 写入执行脚本
        script_path = work_dir / "_run_tests.sh"
        script_path.write_text(run_script)
        script_path.chmod(0o755)

        # 使用 docker volume 传递文件（避免 Windows bind mount 路径问题）
        vol_name = f"sandbox-vol-{submission_id[:8]}"
        helper_name = f"sandbox-helper-{submission_id[:8]}"
        container_name = f"sandbox-{submission_id[:8]}"
        mem = self.memory_limit or "4g"
        cpus = self.cpu_limit or "2"

        start_time = time.time()
        try:
            # 1. 创建 volume
            _docker_cmd(["volume", "create", vol_name])

            # 2. 启动临时容器挂载 volume，用于复制文件
            _docker_cmd([
                "run", "-d", "--name", helper_name,
                "-v", f"{vol_name}:/workspace",
                "busybox", "sleep", "60",
            ])

            # 3. 将项目文件复制到 volume
            _docker_cmd(["cp", str(work_dir) + "/.", f"{helper_name}:/workspace"])

            # 4. 运行分析容器（挂载同一个 volume）
            run_args = [
                "run", "--rm", "--name", container_name,
                "-v", f"{vol_name}:/workspace:rw",
                "-w", "/workspace",
                "--memory", mem,
                "--cpus", cpus,
                "--network", "none",
                "--security-opt", "no-new-privileges:true",
                "--cap-drop", "ALL",
                image,
                "bash", "/workspace/_run_tests.sh",
            ]
            result = _docker_cmd(run_args, timeout=self.timeout)
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

            # 5. 将结果文件复制回主机
            _docker_cmd(["cp", f"{helper_name}:/workspace/test_results.json", str(work_dir / "test_results.json")])
            _docker_cmd(["cp", f"{helper_name}:/workspace/lint.json", str(work_dir / "lint.json")])

        except subprocess.TimeoutExpired:
            logger.warning(f"Sandbox timeout for {submission_id}")
            _docker_cmd(["kill", container_name])
            exit_code = -1
            stdout = ""
            stderr = "timeout"
        finally:
            # 清理
            if script_path.exists():
                script_path.unlink()
            _docker_cmd(["rm", "-f", helper_name])
            _docker_cmd(["volume", "rm", "-f", vol_name])

        elapsed_ms = int((time.time() - start_time) * 1000)

        test_results = self._parse_test_results(work_dir, language)
        static_analysis = self._parse_static_analysis(work_dir, language)
        security_flags = self._check_security_flags(stdout, stderr)

        build_status = "success" if exit_code == 0 else "failed"

        return {
            "build_status": build_status,
            "build_exit_code": exit_code,
            "build_stderr": stderr[:2000],
            "test_results": test_results,
            "static_analysis": static_analysis,
            "security_flags": security_flags,
            "execution_time_ms": elapsed_ms,
            "resource_usage": {"cpu_percent": 0, "memory_mb": 0},
        }

    def _parse_test_results(self, work_dir: Path, language: str) -> Optional[Dict]:
        result_file = work_dir / "test_results.json"
        if not result_file.exists():
            return None
        try:
            data = json.loads(result_file.read_text())
            if language in ("python",):
                summary = data.get("summary", {})
                return {
                    "total": summary.get("total", 0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0),
                    "coverage": summary.get("coverage", 0),
                    "duration_ms": int(summary.get("duration", 0) * 1000),
                }
            else:
                tests = data if isinstance(data, list) else data.get("tests", [])
                passed = sum(1 for t in tests if t.get("status") == "passed")
                return {"total": len(tests), "passed": passed, "failed": len(tests) - passed, "skipped": 0, "coverage": 0, "duration_ms": 0}
        except (json.JSONDecodeError, KeyError):
            return None

    def _parse_static_analysis(self, work_dir: Path, language: str) -> Optional[Dict]:
        lint_file = work_dir / "lint.json"
        if not lint_file.exists():
            return None
        try:
            data = json.loads(lint_file.read_text())
            if isinstance(data, list):
                errors = sum(1 for i in data if i.get("type") == "error" or i.get("severity") in ("error", "fatal"))
                return {"lint_errors": errors, "lint_warnings": len(data) - errors, "avg_complexity": 0, "max_complexity": 0, "duplication": 0, "security_issues": [], "dependency_vulns": []}
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _check_security_flags(self, stdout: str, stderr: str) -> List[str]:
        flags = []
        danger_patterns = ["eval(", "exec(", "__import__", "subprocess.call", "os.system", "shell=True", "pickle.loads", "yaml.load"]
        combined = (stdout + stderr).lower()
        for pattern in danger_patterns:
            if pattern.lower() in combined:
                flags.append(f"potential_danger: {pattern}")
        return flags
