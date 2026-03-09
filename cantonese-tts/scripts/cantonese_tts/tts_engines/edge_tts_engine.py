"""Edge-TTS 引擎插件（免费，使用微软 Edge 在线服务）"""

import asyncio
from pathlib import Path

from ..base import TTSEngine, TTSResult
from ..registry import register_tts_engine

# Edge-TTS 支持的粤语音色
CANTONESE_VOICES = {
    "zh-HK-HiuGaaiNeural": "粤语女声（活泼）",
    "zh-HK-HiuMaanNeural": "粤语女声（温柔）",
    "zh-HK-WanLungNeural": "粤语男声",
}

DEFAULT_VOICE = "zh-HK-HiuGaaiNeural"


@register_tts_engine("edge")
class EdgeTTSEngine(TTSEngine):
    """使用 Edge-TTS（微软免费在线服务）进行粤语语音合成"""

    def __init__(self, voice: str = "", rate: str = "+0%",
                 volume: str = "+0%", pitch: str = "+0Hz", **kwargs):
        self.voice = voice or DEFAULT_VOICE
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        import edge_tts

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _synthesize():
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(str(output_path))

        # 运行异步合成
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    loop.run_in_executor(pool, lambda: asyncio.run(_synthesize()))
            else:
                loop.run_until_complete(_synthesize())
        except RuntimeError:
            asyncio.run(_synthesize())

        voice_desc = CANTONESE_VOICES.get(self.voice, self.voice)

        return TTSResult(
            text=text,
            audio_path=output_path,
            engine_name="edge-tts",
            voice_name=f"{self.voice} ({voice_desc})",
            format=output_path.suffix.lstrip(".") or "mp3",
        )

    def validate(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    def list_voices(self) -> list:
        return [
            {"id": k, "name": v, "gender": "Female" if "Hiu" in k else "Male"}
            for k, v in CANTONESE_VOICES.items()
        ]
