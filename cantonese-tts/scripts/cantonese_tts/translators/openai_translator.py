"""OpenAI 翻译器插件（支持兼容接口如 DeepSeek）"""

from ..base import Translator, TranslationResult
from ..registry import register_translator
from .base_prompt import build_messages, parse_response


@register_translator("openai")
class OpenAITranslator(Translator):
    """使用 OpenAI（或兼容接口）进行普通话→粤语翻译"""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini",
                 base_url: str = "", **kwargs):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or None

    def translate(self, text: str) -> TranslationResult:
        from openai import OpenAI

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)
        messages = build_messages(text)

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )

        cantonese_text = parse_response(response.choices[0].message.content)

        return TranslationResult(
            source_text=text,
            cantonese_text=cantonese_text,
            translator_name="openai",
            model_name=self.model,
            confidence=0.85,
        )

    def validate(self) -> bool:
        return bool(self.api_key)
