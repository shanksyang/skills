"""
Ollama 本地大模型分类器插件
"""

from ..base import AIClassifier, CalendarEvent, Classification
from ..registry import PluginRegistry
from .base_ai import build_prompt, parse_ai_response
from .keyword_classifier import KeywordClassifier


class OllamaClassifier(AIClassifier):
    """Ollama 本地大模型分类器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "qwen2.5:7b")
        self.temperature = config.get("temperature", 0.3)
        self._fallback = KeywordClassifier()

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def validate_config(self) -> list[str]:
        return []

    def classify(self, event: CalendarEvent) -> Classification:
        try:
            import requests

            prompt = build_prompt(event)
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": self.temperature},
                },
                timeout=60,
            )
            resp.raise_for_status()
            result_text = resp.json()["message"]["content"].strip()
            return parse_ai_response(result_text)
        except Exception as e:
            print(f"    ⚠ Ollama 分类失败: {e}，使用规则分类")
            return self._fallback.classify(event)


PluginRegistry.register_classifier("ollama", OllamaClassifier)
