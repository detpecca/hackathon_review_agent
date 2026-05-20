"""
评审Agent基类
- 统一的LLM调用接口（同步 + 异步）
- Prompt模板渲染
- 响应解析和验证
- 重试和错误处理
- Verifier重复验证支持

对应PRD Section 4.2 核心Agent模块
"""
import json
import logging
import statistics
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import jinja2
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Prompt模板加载
_template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("prompts"),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _is_mock_mode(settings: Settings) -> bool:
    """检查是否处于mock模式（无有效API key）"""
    key = settings.openai_api_key or ""
    invalid_prefixes = ("sk-your-", "your-", "sk-mock", "mock", "test")
    return not key or any(key.startswith(p) for p in invalid_prefixes)


def _mock_review(dimension: str) -> Dict[str, Any]:
    """生成mock评审结果（用于开发和测试）"""
    return {
        "score": 65,
        "confidence": 0.75,
        "reason": f"[MOCK] {dimension} review completed. No API key configured.",
        "strengths": ["Structure is clear", "Basic functionality implemented"],
        "weaknesses": ["Needs more testing", "Documentation could be improved"],
        "improvements": ["Add unit tests", "Write README", "Add error handling"],
        "llm_model": "mock",
    }


class BaseReviewAgent(ABC):
    """
    评审Agent抽象基类（支持同步和异步LLM调用）

    子类需实现:
    - template_name: Prompt模板文件名
    - dimension_name: 评审维度标识
    - default_model: 默认LLM模型
    - default_temperature: 采样温度
    """

    template_name: str = ""
    dimension_name: str = ""
    default_model: str = "gpt-4o"
    default_temperature: float = 0.3

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._mock = _is_mock_mode(self.settings)
        if not self._mock:
            self.sync_client = OpenAI(api_key=self.settings.openai_api_key)
            self.async_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        else:
            self.sync_client = None
            self.async_client = None
            logger.warning(f"{self.dimension_name} agent running in MOCK mode")
        self.template = self._load_template()

    def _load_template(self) -> jinja2.Template:
        return _template_env.get_template(self.template_name)

    def _render_prompt(self, context: Dict[str, Any]) -> str:
        return self.template.render(**context)

    def _get_system_prompt(self) -> str:
        try:
            source = self.template.environment.loader.get_source(
                self.template.environment, self.template_name
            )[0]
            if source.strip().startswith("system:"):
                parts = source.split("user:", 1)
                system_block = parts[0].replace("system:", "").strip()
                return system_block
        except Exception:
            pass
        return f"You are an expert {self.dimension_name} reviewer."

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """解析LLM JSON响应，验证必需字段"""
        try:
            data = json.loads(raw)
            assert "score" in data, "Missing 'score' field"
            assert isinstance(data["score"], int), "Score must be int"
            assert 0 <= data["score"] <= 100, "Score out of range"
            assert data["score"] % 5 == 0, "Score must be multiple of 5"
            return data
        except (json.JSONDecodeError, AssertionError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nRaw: {raw[:500]}")
            raise

    # -------------------- 同步调用 --------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _call_llm_sync(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        response = self.sync_client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def review_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """同步评审入口"""
        if self._mock:
            return _mock_review(self.dimension_name)

        prompt = self._render_prompt(context)
        raw_response = self._call_llm_sync(prompt)
        result = self._parse_response(raw_response)
        result["dimension"] = self.dimension_name
        result["llm_model"] = self.default_model
        result["confidence"] = result.get("confidence", 0.7)
        result["raw_response"] = raw_response
        return result

    def review_with_verification_sync(
        self,
        context: Dict[str, Any],
        k: int = 5,
    ) -> Dict[str, Any]:
        """同步Verifier重复验证"""
        if self._mock:
            return _mock_review(self.dimension_name)

        logger.info(f"Starting {self.dimension_name} review with K={k} verifications")
        scores = []
        responses = []
        for i in range(k):
            temp = self.default_temperature + (i * 0.05 - 0.1)
            raw = self._call_llm_sync(
                self._render_prompt(context),
                temperature=max(0.1, min(1.0, temp)),
            )
            parsed = self._parse_response(raw)
            scores.append(parsed["score"])
            responses.append(parsed)

        mean_score = round(statistics.mean(scores) / 5) * 5
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0
        confidence = max(0.0, 1.0 - (std_score / 50.0))
        best_idx = self._select_best_response(responses)
        primary_result = responses[best_idx]
        primary_result["score"] = mean_score
        primary_result["confidence"] = round(confidence, 4)
        primary_result["verification_count"] = k
        primary_result["verification_scores"] = scores
        primary_result["verification_std"] = round(std_score, 4)
        primary_result["dimension"] = self.dimension_name
        return primary_result

    # -------------------- 异步调用 --------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        response = await self.async_client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    async def review(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """异步评审入口"""
        if self._mock:
            return _mock_review(self.dimension_name)

        prompt = self._render_prompt(context)
        raw_response = await self._call_llm(prompt)
        result = self._parse_response(raw_response)
        result["dimension"] = self.dimension_name
        result["llm_model"] = self.default_model
        result["confidence"] = result.get("confidence", 0.7)
        result["raw_response"] = raw_response
        return result

    def _select_best_response(self, responses: List[Dict]) -> int:
        best_idx = 0
        best_score = 0
        for i, r in enumerate(responses):
            score = len(r.get("reason", ""))
            score += len(r.get("strengths", [])) * 20
            score += len(r.get("weaknesses", [])) * 10
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    async def build_context(self, submission_id: str, **kwargs) -> Dict[str, Any]:
        """子类可选实现: 构建评审上下文"""
        return {}
