"""gTTS 引擎插件（免费，使用 Google Translate TTS）"""

from pathlib import Path

from ..base import TTSEngine, TTSResult
from ..registry import register_tts_engine


@register_tts_engine("gtts")
class GTTSEngine(TTSEngine):
    """使用 gTTS（Google Translate TTS）进行粤语语音合成"""

    def __init__(self, lang: str = "zh-TW", slow: bool = False, **kwargs):
        # gTTS 对粤语的支持：zh-TW 比 zh-CN 更接近粤语发音
        # 也可尝试 "yue"（粤语 ISO 639-3 代码），部分版本支持
        self.lang = lang
        self.slow = slow

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        from gtts import gTTS

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 尝试使用粤语代码，失败则降级
        lang_to_try = [self.lang]
        if self.lang not in ("zh-TW", "zh-CN"):
            lang_to_try.append("zh-TW")

        last_error = None
        for lang in lang_to_try:
            try:
                tts = gTTS(text=text, lang=lang, slow=self.slow)
                tts.save(str(output_path))
                used_lang = lang
                break
            except Exception as e:
                last_error = e
                continue
        else:
            raise last_error or RuntimeError("gTTS 合成失败")

        return TTSResult(
            text=text,
            audio_path=output_path,
            engine_name="gtts",
            voice_name=f"Google TTS ({used_lang})",
            format="mp3",
        )

    def validate(self) -> bool:
        try:
            from gtts import gTTS
            return True
        except ImportError:
            return False

    def list_voices(self) -> list:
        return [
            {"id": "zh-TW", "name": "Google TTS (台湾中文/近似粤语)", "gender": "Unknown"},
            {"id": "yue", "name": "Google TTS (粤语)", "gender": "Unknown"},
        ]
