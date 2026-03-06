"""
智谱 AI 分类器插件
"""

from ..base import AIClassifier, CalendarEvent, Classification
from ..registry import PluginRegistry
from .base_ai import build_prompt, parse_ai_response
from .keyword_classifier import KeywordClassifier


class ZhipuClassifier(AIClassifier):
    """智谱 AI (GLM) 分类器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "glm-4-flash")
        self.temperature = config.get("temperature", 0.3)
        self._fallback = KeywordClassifier()

    @property
    def name(self) -> str:
        return f"智谱 AI ({self.model})"

    def validate_config(self) -> list[str]:
        if not self.api_key:
            return ["ai.api_key (ZHIPU_API_KEY)"]
        return []

    def classify(self, event: CalendarEvent) -> Classification:
        if not self.api_key:
            return self._fallback.classify(event)

        try:
            import zhipuai
            client = zhipuai.ZhipuAI(api_key=self.api_key)

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
            print(f"    ⚠ 智谱 AI 分类失败: {e}，使用规则分类")
            return self._fallback.classify(event)


PluginRegistry.register_classifier("zhipu", ZhipuClassifier)
