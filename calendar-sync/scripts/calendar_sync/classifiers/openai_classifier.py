"""
OpenAI 分类器插件 - 支持 OpenAI API 及兼容接口（DeepSeek、通义千问等）
"""

from ..base import AIClassifier, CalendarEvent, Classification
from ..registry import PluginRegistry
from .base_ai import build_prompt, parse_ai_response
from .keyword_classifier import KeywordClassifier


class OpenAIClassifier(AIClassifier):
    """OpenAI / OpenAI 兼容 API 分类器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.3)
        self._fallback = KeywordClassifier()

    @property
    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def validate_config(self) -> list[str]:
        if not self.api_key:
            return ["ai.api_key (OPENAI_API_KEY)"]
        return []

    def classify(self, event: CalendarEvent) -> Classification:
        if not self.api_key:
            return self._fallback.classify(event)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            prompt = build_prompt(event)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=300,
            )

            result_text = response.choices[0].message.content.strip()
            return parse_ai_response(result_text)
        except Exception as e:
            print(f"    ⚠ OpenAI 分类失败: {e}，使用规则分类")
            return self._fallback.classify(event)


PluginRegistry.register_classifier("openai", OpenAIClassifier)
