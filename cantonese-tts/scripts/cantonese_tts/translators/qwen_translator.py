"""通义千问翻译器插件"""

from ..base import Translator, TranslationResult
from ..registry import register_translator
from .base_prompt import build_messages, parse_response


@register_translator("qwen")
class QwenTranslator(Translator):
    """使用通义千问进行普通话→粤语翻译"""

    def __init__(self, api_key: str = "", model: str = "qwen-turbo",
                 base_url: str = "", **kwargs):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def translate(self, text: str) -> TranslationResult:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
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
            translator_name="qwen",
            model_name=self.model,
            confidence=0.85,
        )

    def validate(self) -> bool:
        return bool(self.api_key)
