"""
Anthropic Claude 分类器插件
"""

from ..base import AIClassifier, CalendarEvent, Classification
from ..registry import PluginRegistry
from .base_ai import build_prompt, parse_ai_response
from .keyword_classifier import KeywordClassifier


class ClaudeClassifier(AIClassifier):
    """Anthropic Claude 分类器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 300)
        self._fallback = KeywordClassifier()

    @property
    def name(self) -> str:
        return f"Claude ({self.model})"

    def validate_config(self) -> list[str]:
        if not self.api_key:
            return ["ai.api_key (ANTHROPIC_API_KEY)"]
        return []

    def classify(self, event: CalendarEvent) -> Classification:
        if not self.api_key:
            return self._fallback.classify(event)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = build_prompt(event)
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = response.content[0].text.strip()
            return parse_ai_response(result_text)
        except Exception as e:
            print(f"    ⚠ Claude 分类失败: {e}，使用规则分类")
            return self._fallback.classify(event)


PluginRegistry.register_classifier("claude", ClaudeClassifier)
