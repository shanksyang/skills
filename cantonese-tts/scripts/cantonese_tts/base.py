"""基类定义：翻译器和 TTS 引擎的抽象接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class TranslationResult:
    """翻译结果"""
    source_text: str          # 原始普通话文本
    cantonese_text: str       # 粤语文本
    translator_name: str      # 使用的翻译器名称
    model_name: str = ""      # 使用的模型名称
    confidence: float = 0.0   # 置信度 (0-1)
    notes: str = ""           # 翻译备注


@dataclass
class TTSResult:
    """TTS 合成结果"""
    text: str                 # 合成的文本
    audio_path: Path          # 音频文件路径
    engine_name: str          # 使用的 TTS 引擎名称
    voice_name: str = ""      # 音色名称
    duration_ms: int = 0      # 音频时长（毫秒）
    format: str = "mp3"       # 音频格式


@dataclass
class ConversionResult:
    """完整的转换结果（翻译 + TTS）"""
    translation: TranslationResult
    tts: Optional[TTSResult] = None


class Translator(ABC):
    """翻译器抽象基类"""

    name: str = "base"

    @abstractmethod
    def translate(self, text: str) -> TranslationResult:
        """将普通话文本翻译为粤语文本"""
        pass

    def validate(self) -> bool:
        """验证翻译器配置是否有效"""
        return True


class TTSEngine(ABC):
    """TTS 引擎抽象基类"""

    name: str = "base"

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        """将粤语文本合成为语音文件"""
        pass

    def validate(self) -> bool:
        """验证 TTS 引擎配置是否有效"""
        return True

    def list_voices(self) -> list:
        """列出可用的粤语音色"""
        return []
