"""智谱 AI 翻译器插件"""

from ..base import Translator, TranslationResult
from ..registry import register_translator
from .base_prompt import build_messages, parse_response


@register_translator("zhipu")
class ZhipuTranslator(Translator):
    """使用智谱 AI (GLM) 进行普通话→粤语翻译"""

    def __init__(self, api_key: str = "", model: str = "glm-4-flash", **kwargs):
        self.api_key = api_key
        self.model = model

    def translate(self, text: str) -> TranslationResult:
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=self.api_key)
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
            translator_name="zhipu",
            model_name=self.model,
            confidence=0.85,
        )

    def validate(self) -> bool:
        return bool(self.api_key)
